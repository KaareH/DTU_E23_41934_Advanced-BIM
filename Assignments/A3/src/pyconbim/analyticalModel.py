"""
AnalyticalModel

Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

from abc import ABC, abstractmethod

import ifcopenshell
import ifcopenshell.util.representation
import ifcopenshell.geom.occ_utils
import ifcopenshell.api.geometry
from ifcopenshell.api import run

from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.NCollection import NCollection_Mat4
from OCC.Core.TopLoc import TopLoc_Location

import pyconbim.geomUtils as geomUtils
import pyconbim.rendering as rendering

class Knot3D:
    def __init__(self) -> None:
        pass

class StructuralMember(ABC):
    """"Abstract class for structural members"""

    def __init__(self, GUID) -> None:
        self.GUID = GUID
        self.nodes = []

class PhysicalMember(StructuralMember, ABC):
    def __init__(self, GUID) -> None:
        super().__init__(GUID)
    
    @abstractmethod
    def to_ifc_structuralMember(self, model):
        pass

class VirtualMember(StructuralMember):
    """Very stiff virtual member for connections"""
    
    def __init__(self, key, axis, member1, member2) -> None:
        super().__init__(key)
        self.key = key
        self.axis = axis
        self.member1 = member1
        self.member2 = member2

class AxialMember(PhysicalMember):
    """Abstract class for axial members"""

    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID)
        assert geomUtils.is_wire_straight_line(axis)
        self.axis = axis

    def to_ifc_structuralMember(self, model):
        """
        Return IfcStructuralCurveMember

        https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcStructuralCurveMember.htm
        """
        super().to_ifc_structuralMember(model)
        # TODO: Add direction, currently not correct
        # TODO: Use axis instead of endpoints. Use IfcEdgeCurve instead of IfcEdge

        # Find unit-scale and transform shape
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
        location = self.axis.Location()
        transformation = location.Transformation()
        scaleFactor = float(1.0/unit_scale)

        transformation.SetScaleFactor(scaleFactor)
        location = TopLoc_Location(transformation)
        wireShape = self.axis.Located(location, False)

        name = f"{type(self).__name__}"
        description = f"Analytical model for {self.GUID}. Created with {type(self)}."
        direction = model.createIfcDirection((1., 0., 0.))
        curveMember = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcStructuralCurveMember", predefined_type="RIGID_JOINED_MEMBER")
        curveMember = ifcopenshell.api.run("root.create_entity", model, name=name,
                ifc_class="IfcStructuralCurveMember", predefined_type="RIGID_JOINED_MEMBER")
        curveMember.Description = description
        curveMember.Axis = direction

        p1, p2 = geomUtils.get_wire_endpoints(wireShape)
        P1 = model.create_entity("IfcCartesianPoint", **{"Coordinates": p1.Coord()})
        P2 = model.create_entity("IfcCartesianPoint", **{"Coordinates": p2.Coord()})
        V1 = model.create_entity("IfcVertexPoint", **{"VertexGeometry": P1})
        V2 = model.create_entity("IfcVertexPoint", **{"VertexGeometry": P2})

        edge = model.create_entity("IfcEdge", **{
            "EdgeStart": V1,
            "EdgeEnd": V2,})

        context = ifcopenshell.util.representation.get_context(model, "Model")
        topologyRepresentation = model.createIfcTopologyRepresentation(ContextOfItems=context,
                    Items=[edge], RepresentationIdentifier="Reference", RepresentationType="Edge")

        # productDefinitionShape = ifcopenshell.geom.serialise(model.schema, self.axis)

        ifcopenshell.api.run("geometry.assign_representation", model, product=curveMember, representation=topologyRepresentation)

        return curveMember

import ifcopenshell.util.unit
class PlanarMember(PhysicalMember):
    """Abstract class for planar members"""

    def __init__(self, GUID, surface, plane) -> None:
        super().__init__(GUID)
        # Do assert here
        self.surface = surface
        self.plane = plane

    def to_ifc_structuralMember(self, model):
        """
        Return IfcStructuralSurfaceMember

        https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcStructuralSurfaceMember.htm
        """
        super().to_ifc_structuralMember(model)

        # Find unit-scale and tranform shape
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
        location = self.surface.Location()
        transformation = location.Transformation()
        scaleFactor = float(1.0/unit_scale)

        transformation.SetScaleFactor(scaleFactor)
        location = TopLoc_Location(transformation)
        surfaceShape = self.surface.Located(location, False)

        name = f"{type(self).__name__}"
        description = f"Analytical model for {self.GUID}. Created with {type(self)}."
        # TODO: Add local placement
        surfaceMember = ifcopenshell.api.run("root.create_entity", model, name=name,
                ifc_class="IfcStructuralSurfaceMember", predefined_type="SHELL")
        surfaceMember.Description = description
        
        plane, outerCurve, innerCurves = geomUtils.deconstruct_face(surfaceShape)
        wire_outerCurve = outerCurve
        
        outerCurve = ifcopenshell.geom.serialise(model.schema, outerCurve)
        innerCurves = [ifcopenshell.geom.serialise(model.schema, innerCurve) for innerCurve in innerCurves]

        # Make polyline
        vertices = list()
        explorer = BRepTools_WireExplorer(wire_outerCurve, surfaceShape)
        while explorer.More():
            edge = explorer.Current()
            vertex = explorer.CurrentVertex()
            explorer.Next()
            vertices.append(vertex)

        # TODO: Check if vertices are in correct order. Gives wrong surface if not
        points = []
        for vert in vertices:
            pnt = BRep_Tool.Pnt(vert)
            ifcPnt = model.create_entity("IfcCartesianPoint", **{"Coordinates": [*pnt.Coord()]})
            points.append(ifcPnt)

        polyline = model.create_entity("IfcPolyline", **{
            "Points": points,
        })

        outerCurve = polyline

        # Create plane
        plane = model.create_entity("IfcPlane", **{
            "Position": model.create_entity("IfcAxis2Placement3D", **{
                "Location": model.create_entity("IfcCartesianPoint", **{"Coordinates": [*self.plane.Location().Coord()]}),
                "Axis": model.create_entity("IfcDirection", **{"DirectionRatios": [*self.plane.Axis().Direction().Coord()]}),
                "RefDirection": model.create_entity("IfcDirection", **{"DirectionRatios": [*self.plane.XAxis().Direction().Coord()]}),
            }),
        })

        # TODO: Add inner boundaries
        # https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcCurveBoundedPlane.htm
        surface = model.create_entity("IfcCurveBoundedPlane", **{
            "BasisSurface": plane,
            "OuterBoundary": outerCurve,
            # "InnerBoundaries": innerCurves,
            "InnerBoundaries": [],
        })

        polyloop = model.create_entity("IfcPolyLoop", **{  
            "Polygon": points,
        })

        facebound = model.create_entity("IfcFaceBound", **{
            "Bound": polyloop,
            "Orientation": True,
        })

        faceSurface =  model.create_entity("IfcFaceSurface", **{
            "Bounds": [facebound],
            "FaceSurface": surface,
            "SameSense": True,
           })

        context = ifcopenshell.util.representation.get_context(model, "Model")
        topologyRepresentation = model.createIfcTopologyRepresentation(
            ContextOfItems=context, Items=[faceSurface],
            RepresentationIdentifier="Reference", RepresentationType="Face")

        ifcopenshell.api.run("geometry.assign_representation", model, product=surfaceMember, representation=topologyRepresentation)

        return surfaceMember

class Beam(AxialMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID, axis)

class Column(AxialMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID, axis)

class Slab(PlanarMember):
    def __init__(self, GUID, surface, plane) -> None:
        super().__init__(GUID, surface, plane)

class Wall(PlanarMember):
    def __init__(self, GUID, surface, plane) -> None:
        super().__init__(GUID, surface, plane)

class Footing(PhysicalMember):
    """Footing. This is a special member, as it defines boundary conditions for the model"""

    def __init__(self, GUID, body, pnt) -> None:
        super().__init__(GUID)
        self.body = body
        self.pnt = pnt

    def to_ifc_structuralMember(self, model):
        super().to_ifc_structuralMember(model)
        pass

class AnalyticalModel:
    """
        Container for analytical structal members.
        
        Supports creating model as a IfcStructuralAnalysisModel.
    """

    def __init__(self) -> None:
        self.members = dict()

    def addMember(self, member) -> None:
        if isinstance(member, PhysicalMember):
            assert self.members.get(member.GUID) is None
            self.members[member.GUID] = member

        elif isinstance(member, VirtualMember):
            assert self.members.get(member.key) is None
            self.members[member.key] = member

        else:
            raise TypeError(f"Unknown member type: {type(member)}")
    
    def to_ifc_analysisModel(self, model):
        """"Return model as a IfcStructuralAnalysisModel with structural members"""

        # Create analysis model
        analysisModel = run("root.create_entity", model, ifc_class="IfcStructuralAnalysisModel", predefined_type="LOADING_3D")
        # run("type.assign_type", model, related_object=analysisModel, relating_type=element_type)
        
        # Assing to building
        buildings = model.by_type("IfcBuilding")
        assert len(buildings) == 1
        building = buildings[0]
        run("aggregate.assign_object", model, relating_object=building, product=analysisModel)
        
        # Create structural members
        curveMembers = []
        surfaceMembers = []
        for member in self.members.values():
            if isinstance(member, AxialMember):
                curveMembers.append(member.to_ifc_structuralMember(model))
            elif isinstance(member, PlanarMember):
                surfaceMembers.append(member.to_ifc_structuralMember(model))
            else:
                pass
                #raise TypeError(f"Unknown member type: {type(member)}")
        
        print("Curve members:", len(curveMembers))
        print("Surface members:", len(surfaceMembers))

        # Assign to analysis model
        ifcopenshell.api.run("group.assign_group", model,
                    products=curveMembers, group=analysisModel)
        
        ifcopenshell.api.run("group.assign_group", model,
                    products=surfaceMembers, group=analysisModel)

        return analysisModel
                
class KeyGenerator:
    def __init__(self):
        self.keys = dict()
        self.counter = 0

    def generate(self, prefix, longKey):
        self.counter += 1
        shortKey = f"{prefix}_{self.counter}"
        self.keys[shortKey] = longKey

        return shortKey
    
def make_virtual_member(key1, key2, p1, p2):
    """Very stiff member for connections"""
    distance = geomUtils.distance_between_points(p1, p2)
    
    TOLERANCE = 0.0001
    if distance <= TOLERANCE:
        return None
    try:
        wire = geomUtils.make_wire_from_points([p1, p2])
    except Exception as e:
        print(e)
        print(p1.Coord())
        print(p2.Coord())
        return None
    
    key = ('Virt', key1, key2)
    member = VirtualMember(key=key, axis=wire, member1=key1, member2=key2)
    return member

