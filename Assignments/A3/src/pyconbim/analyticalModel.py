# Kaare G. S. Hansen, s214282 - DTU
# 41934 - Advanced BIM, E23

""" AnalyticalModel.

This module acts as a middleman for interportation of actual geometry of
members, and the conversion to idealized analytical members.
"""

from abc import ABC, abstractmethod
from loguru import logger
from collections import namedtuple
import numpy as np

import ifcopenshell
import ifcopenshell.util.representation
import ifcopenshell.geom.occ_utils
import ifcopenshell.api.geometry
from ifcopenshell.api import run
import ifcopenshell.util.unit

import pyconbim.geomUtils as geomUtils
import pyconbim.rendering as rendering
import pyconbim.utils as utils

from OCC.Core.gp import gp_Pnt

# TODO:Shared Object placement: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcStructuralAnalysisModel.htm

class Knot3D:
    def __init__(self) -> None:
        pass

class StructuralMember(ABC):
    """"Abstract class for structural members"""

    def __init__(self, GUID) -> None:
        self.GUID = GUID
        self.nodes = []
        self.ifcStructuralItem = None

class PhysicalMember(StructuralMember, ABC):
    def __init__(self, GUID, OBB) -> None:
        super().__init__(GUID)
        self.OBB = OBB
    
    @abstractmethod
    def to_ifc_structuralMember(self, model):
        assert self.ifcStructuralItem is None

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

    def __init__(self, elementData) -> None:
        super().__init__(elementData.GUID, elementData.OBB)
        # Axis from ifcopenshell might not even be inside the OBB of the element.
        # Hence not usable at all.
        
        wire = geomUtils.convert_bnd_to_line(elementData.OBB, returnWire=True)
        assert 'Axis' in elementData.keys

        axis = elementData.shapes['Axis'].geometry

        subShapes = geomUtils.get_subShapes(axis)
        assert len(subShapes) == 1
            
        shape = subShapes[0]
        assert geomUtils.is_wire_straight_line(shape)

        self.axis = wire
        assert geomUtils.is_wire_straight_line(self.axis)


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
        scaleFactor = float(1.0/unit_scale)

        # Move shape to orign with local transformation
        wireShape, transformation = geomUtils.transform_to_local(self.axis, scaleFactor)

        # Get matrix for IfcLocalPlacement
        matrix = utils.getAffineTransformation(transformation)

        # Create entity
        name = f"{type(self).__name__}"
        description = f"Analytical model for {self.GUID}. Created with {type(self)}."
        direction = model.createIfcDirection((1., 0., 0.))
        curveMember = ifcopenshell.api.run("root.create_entity", model, name=name,
                ifc_class="IfcStructuralCurveMember", predefined_type="RIGID_JOINED_MEMBER")
        curveMember.Description = description
        curveMember.Axis = direction

        run("geometry.edit_object_placement", model, product=curveMember,
            matrix=matrix, is_si=True)
            # matrix=matrix, is_si=False)

        # Should wireShape be transformed back to global coordinates?
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

class PlanarMember(PhysicalMember):
    """Abstract class for planar members"""

    def __init__(self, elementData) -> None:
        super().__init__(elementData.GUID, elementData.OBB)
        plane = geomUtils.convert_bnd_to_plane(elementData.OBB)
        planeface = geomUtils.get_planeface(plane)

        commonSurface = geomUtils.find_solid_face_intersection(elementData.body, planeface)
 
        self.surface = commonSurface
        self.plane = plane

    def to_ifc_structuralMember(self, model):
        """
        Return IfcStructuralSurfaceMember

        https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcStructuralSurfaceMember.htm
        """
        super().to_ifc_structuralMember(model)

        # Find unit-scale and tranform shape
        unit_scale = ifcopenshell.util.unit.calculate_unit_scale(model)
        scaleFactor = float(1.0/unit_scale)

        # Move shape to orign with local transformation
        surfaceShape, transformation = geomUtils.transform_to_local(self.surface, scaleFactor)

        # Get matrix for IfcLocalPlacement
        matrix = utils.getAffineTransformation(transformation)

        # Create entity
        name = f"{type(self).__name__}"
        description = f"Analytical model for {self.GUID}. Created with {type(self)}."
        # TODO: Add local placement
        surfaceMember = ifcopenshell.api.run("root.create_entity", model, name=name,
                ifc_class="IfcStructuralSurfaceMember", predefined_type="SHELL")
        surfaceMember.Description = description
        
        run("geometry.edit_object_placement", model, product=surfaceMember,
            matrix=matrix, is_si=True)
            # matrix=matrix, is_si=False)

        plane, outerCurve, innerCurves = geomUtils.deconstruct_face(surfaceShape)
        wire_outerCurve = outerCurve
        wire_innerCurves = innerCurves
        
        def make_polyline_adaptive(wire, surfaceShape):
            points = geomUtils.adaptive_wire_to_polyline(wire, surfaceShape)

            ifcPoints = []
            for pnt in points:
                ifcPnt = model.create_entity("IfcCartesianPoint", **{"Coordinates": [*pnt.Coord()]})
                ifcPoints.append(ifcPnt)

            polyline = model.create_entity("IfcPolyline", **{
                "Points": ifcPoints,
            })

            return polyline, ifcPoints

        outerCurve, points = make_polyline_adaptive(wire_outerCurve, surfaceShape)
        innerCurves = [make_polyline_adaptive(wire_innerCurve, surfaceShape) for wire_innerCurve in wire_innerCurves]
        innerPointsList = [innerCurve[1] for innerCurve in innerCurves]
        innerCurves = [innerCurve[0] for innerCurve in innerCurves]

        # Create plane
        plane = model.create_entity("IfcPlane", **{
            "Position": model.create_entity("IfcAxis2Placement3D", **{
                "Location": model.create_entity("IfcCartesianPoint", **{"Coordinates": [0.0, 0.0, 0.0]}),
                "Axis": model.create_entity("IfcDirection", **{"DirectionRatios": [0.0, 0.0, 1.0]}),
                "RefDirection": model.create_entity("IfcDirection", **{"DirectionRatios": [1.0, 0.0, 0.0]}),
            }),
        })

        # https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcCurveBoundedPlane.htm
        surface = model.create_entity("IfcCurveBoundedPlane", **{
            "BasisSurface": plane,
            "OuterBoundary": outerCurve,
            "InnerBoundaries": innerCurves,
        })

        innerFaceBounds = []
        for innerPoints in innerPointsList:
            polyloop = model.create_entity("IfcPolyLoop", **{  
                "Polygon": innerPoints,
            })

            facebound = model.create_entity("IfcFaceBound", **{
                "Bound": polyloop,
                "Orientation": True,
            })
            innerFaceBounds.append(facebound)

        polyloop = model.create_entity("IfcPolyLoop", **{  
            "Polygon": points,
        })

        facebound = model.create_entity("IfcFaceBound", **{
            "Bound": polyloop,
            "Orientation": True,
        })

        faceSurface =  model.create_entity("IfcFaceSurface", **{
            "Bounds": [facebound, *innerFaceBounds],
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
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Column(AxialMember):
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Slab(PlanarMember):
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Wall(PlanarMember):
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Footing(PhysicalMember):
    """Footing. This is a special member, as it defines boundary conditions for the model"""

    def __init__(self, elementData) -> None:
        super().__init__(elementData.GUID, elementData.OBB)
        self.body = elementData.body
        self.pnt = gp_Pnt(elementData.OBB.Center())
        logger.warning(self.pnt)

    def to_ifc_structuralMember(self, model):
        super().to_ifc_structuralMember(model)
        pass

ElementData = namedtuple('ElementData', ['GUID', 'element', 'shapes', 'keys', 'OBB', 'body'])

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
        
        logger.info(f"Curve members: {len(curveMembers)}")
        logger.info(f"Surface members: {len(surfaceMembers)}")

        # Assign to analysis model
        ifcopenshell.api.run("group.assign_group", model,
                    products=curveMembers, group=analysisModel)
        
        ifcopenshell.api.run("group.assign_group", model,
                    products=surfaceMembers, group=analysisModel)

        return analysisModel
    
    def add_elements(self, elements, modelData):
        """Add structural members from elements"""

        elementFunctions = {
            "IfcBeam": Beam,
            "IfcColumn": Column,
            "IfcSlab": Slab,
            "IfcWall": Wall,
            "IfcFooting": Footing,
        }

        model = modelData.model
        addCount = 0
        for GUID in elements:
            shapes = modelData.shapes[GUID]
            keys = shapes.keys()
            element = modelData.model.by_guid(GUID)
            
            assert 'Body' in keys
            OBB = modelData.obbs[GUID]
            body = shapes['Body'].geometry
            
            # Assert that an element doesn't have both Axis and FootPrint
            assert not ('Axis' in keys and 'FootPrint' in keys)

            elementData = ElementData(
                GUID = GUID,
                element = element,
                shapes = shapes,
                keys = keys,
                OBB = OBB,
                body = body,
            )

            IfcClass = element.is_a()

            if IfcClass in elementFunctions.keys():
                member = elementFunctions[IfcClass](elementData)
                self.addMember(member)
                addCount += 1
            else:
                logger.warning(f"Function for {IfcClass} not implemented! Skipping element...")
        
        logger.info(f"Added {addCount}/{len(elements)} members to analytical model.")
                
    def solve_connection_axial_axial(self, member1: AxialMember, member2: AxialMember) -> VirtualMember:
        """Solve connection between two axial members"""
        wire1 = member1.axis
        wire2 = member2.axis

        p1, p2 = geomUtils.find_closest_points(wire1, wire2)
        virtualMember = make_virtual_member(member1.GUID, member2.GUID, p1, p2)
        return virtualMember

    def solve_connection_axial_planar(self, axialMember: AxialMember, planarMember: PlanarMember) -> VirtualMember:
        """Solve connection between axial and planar member"""
        axis = axialMember.axis
        planarSurface = planarMember.surface

        p1, p2 = geomUtils.find_closest_points(axis, planarSurface)

        virtualMember = make_virtual_member(axialMember.GUID, planarMember.GUID, p1, p2)
        return virtualMember

    def solve_connection_planar_planar(self, member1: PlanarMember, member2: PlanarMember) -> VirtualMember:
        """Solve connection between two planar members"""
        return None
    
    def solve_connections(self) -> None:
        """Solve connections between members"""
        
        logger.info("Solving connections...")
        physicalMembers = {key: member for key, member in self.members.items() if isinstance(member, PhysicalMember)}
        OBBs = {GUID: member.OBB for GUID, member in physicalMembers.items()}

        _, element_collisions = geomUtils.find_collisions(OBBs)
        collision_pairs = find_collisions_pairs(element_collisions)
        logger.debug(f"Collision pairs: {len(collision_pairs)}")

        for collision in collision_pairs:
            key1 = collision[0]
            key2 = collision[1]

            member1 = self.members[key1]
            member2 = self.members[key2]

            virtualMember = None
            if isinstance(member1, AxialMember) and isinstance(member2, AxialMember):
                virtualMember = self.solve_connection_axial_axial(member1, member2)
            
            elif isinstance(member1, PlanarMember) and isinstance(member2, PlanarMember):
                virtualMember = self.solve_connection_planar_planar(member1, member2)
            
            elif ((isinstance(member1, AxialMember) and isinstance(member2, PlanarMember))
                  or
                  (isinstance(member2, AxialMember) and isinstance(member1, PlanarMember))):
                if isinstance(member1, PlanarMember):
                    axialMember = member2
                    planarMember = member1
                else:
                    axialMember = member1
                    planarMember = member2
                virtualMember = self.solve_connection_axial_planar(axialMember, planarMember)
                
            elif (isinstance(member1, AxialMember) and isinstance(member2, Footing)
                or
                isinstance(member2, AxialMember) and isinstance(member1, Footing)):
                if isinstance(member1, Footing):
                    footing = member1
                    axialMember = member2
                else:
                    footing = member2
                    axialMember = member1
                
                axis = axialMember.axis

                # print(footing.pnt)
                # pnt = gp_Pnt(footing.pnt)

                p1, p2 = geomUtils.find_closest_points(axis, footing.body)
                virtualMember = make_virtual_member(key1, key2, p1, p2)

                # Assuming p1 is on the footing
                footing.pnt = p1

                if virtualMember == None:
                    continue
            else:
                logger.warning(f"Unknown connection between {type(member1)} and {type(member2)}")
                continue

            if virtualMember == None:
                continue
            self.addMember(virtualMember)

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
        logger.exception(e)
        logger.exception(p1.Coord())
        logger.exception(p2.Coord())
        return None
    
    key = ('Virt', key1, key2)
    member = VirtualMember(key=key, axis=wire, member1=key1, member2=key2)
    return member

def find_collisions_pairs(element_collisions):
    """Find collision pairs from element collisions.

    Collision pairs are defined as a tuple of two sorted GUIDs - hence
    (A, B) will exist, but not (B, A).
    """
    collision_pairs = set()

    for key, collisions in element_collisions.items():
        for collision in collisions:
            this_key = tuple(sorted([key, collision]))
            collision_pairs.add(this_key)
    
    return collision_pairs

