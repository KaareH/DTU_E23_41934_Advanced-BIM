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
import pyconbim.ifcUtils as ifcutils
import pyconbim.utils as utils

from OCC.Core.gp import gp_Pnt

# TODO:Shared Object placement: https://ifc43-docs.standards.buildingsmart.org/IFC/RELEASE/IFC4x3/HTML/lexical/IfcStructuralAnalysisModel.htm

GENERAL_TOLERANCE = 0.0001

class StructuralConnection(ABC):
    def __init__(self) -> None:
        pass

    @abstractmethod
    def to_ifc_structuralConnection(self, model):
        """"Create object as entity in IfcModel"""
        pass

class Knot3D(StructuralConnection):
    def __init__(self, key, point: gp_Pnt, member) -> None:
        self.key = key
        self.point = point
        self.members = list()
        self.boundaryCondition = None

        self.addMember(member)

    def addMember(self, member):
        member.add_node(self)
        self.members.append(member)

    def clearMembers(self):
        for member in self.members:
            member.remove_node(self)
        self.members = []

    def get_point(self) -> gp_Pnt:
        return self.point
    
    def is_equal(self, other_knot) -> bool:
        isClose = geomUtils.distance_between_points(self.get_point(), other_knot.get_point()) < GENERAL_TOLERANCE
        return isClose
    
    def is_destroyed(self) -> bool:
        return self.point is None
    
    def destroy(self):
        self.clearMembers()
        self.point = None
    
    def merge_nodes(self, other_knot):
        """Merge two nodes that are close to each other"""
        assert self.is_equal(other_knot)

        for member in other_knot.members:
            self.addMember(member)
        
        other_knot.destroy()

    def to_ifc_structuralConnection(self, model):
        """Create IfcStructuralPointConnection in IfcModel"""
        name = f"{type(self).__name__}"
        description = f"Node {self.key}"
        pointConnection = ifcopenshell.api.run("root.create_entity", model, name=name,
                ifc_class="IfcStructuralPointConnection")
        pointConnection.Description = description

        vertex = ifcutils.createIfcVertexPoint(self.get_point(), model)

        context = ifcopenshell.util.representation.get_context(model, "Model")
        topologyRepresentation = model.createIfcTopologyRepresentation(ContextOfItems=context,
                    Items=[vertex], RepresentationIdentifier="Reference", RepresentationType="Vertex")

        # TODO: add related members

        # TODO: add better boundary conditions
        if self.boundaryCondition == "Fixed":
            boundaryNodeCondition = model.create_entity("IfcBoundaryNodeCondition", **{
                "Name": "Fixed",
                "TranslationalStiffnessX": model.createIfcBoolean(True),
                "TranslationalStiffnessY": model.createIfcBoolean(True),
                "TranslationalStiffnessZ": model.createIfcBoolean(True),
                "RotationalStiffnessX": model.createIfcBoolean(True),
                "RotationalStiffnessY": model.createIfcBoolean(True),
                "RotationalStiffnessZ": model.createIfcBoolean(True),
            })

            pointConnection.AppliedCondition = boundaryNodeCondition

        ifcopenshell.api.run("geometry.assign_representation", model, product=pointConnection, representation=topologyRepresentation)

        return pointConnection

class StructuralMember(ABC):
    """Abstract class for structural members"""

    def __init__(self, GUID) -> None:
        self.GUID = GUID
        self.nodes = []
        self.ifcStructuralItem = None
    
    def add_node(self, node):
        self.nodes.append(node)

    def remove_node(self, node):
        self.nodes.remove(node)

    def get_nodes(self):
        return self.nodes

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

        # assert 'Axis' in elementData.keys

        # axis = elementData.shapes['Axis'].geometry

        # subShapes = geomUtils.get_subShapes(axis)
        # assert len(subShapes) == 1
            
        # shape = subShapes[0]
        # assert geomUtils.is_wire_straight_line(shape)

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
        # TODO: Use IfcVertexPoint from nodes

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

        V1 = ifcutils.createIfcVertexPoint(p1, model)
        V2 = ifcutils.createIfcVertexPoint(p2, model)

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

class Pile(AxialMember):
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Slab(PlanarMember):
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Wall(PlanarMember):
    def __init__(self, elementData) -> None:
        super().__init__(elementData)

class Footing(PlanarMember):
    """Footing. This is a special member, as it defines boundary conditions for the model"""

    def __init__(self, elementData) -> None:
        super().__init__(elementData)

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
        self.keyGenerator = KeyGenerator()

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
        
        # Create point connections
        pointConnections = []
        nodes = self.get_nodes()
        for key, node in nodes.items():
            if isinstance(node, Knot3D):
                pointConnection = node.to_ifc_structuralConnection(model)
                pointConnections.append(pointConnection)
            else:
                logger.warning(f"Unknown node type: {type(node)}, key: {key}")

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
        
        logger.info(f"Point connections: {len(pointConnections)}")
        logger.info(f"Curve members: {len(curveMembers)}")
        logger.info(f"Surface members: {len(surfaceMembers)}")

        # Assign to analysis model
        ifcopenshell.api.run("group.assign_group", model,
                    products=pointConnections, group=analysisModel)
        
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
            "IfcPile": Pile,
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
                
    def solve_connection_axial_axial(self, member1: AxialMember, member2: AxialMember) -> VirtualMember | None:
        """Solve connection between two axial members"""
        wire1 = member1.axis
        wire2 = member2.axis

        for member in [member1, member2]:
            p1, p2 = geomUtils.get_wire_endpoints(member.axis)
            Knot3D(self.keyGenerator.generate('N'), p1, member)
            Knot3D(self.keyGenerator.generate('N'), p2, member)

        p1, p2 = geomUtils.find_closest_points(wire1, wire2)
        virtualMember = make_virtual_member(member1.GUID, member2.GUID, p1, p2)
        return virtualMember

    def solve_connection_axial_planar(self, axialMember: AxialMember, planarMember: PlanarMember) -> VirtualMember | None:
        """Solve connection between axial and planar member"""
        axis = axialMember.axis
        planarSurface = planarMember.surface

        p1, p2 = geomUtils.find_closest_points(axis, planarSurface)

        # virtualMember = make_virtual_member(axialMember.GUID, planarMember.GUID, p1, p2)
        # return virtualMember
        return None

    def solve_connection_planar_planar(self, member1: PlanarMember, member2: PlanarMember) -> VirtualMember | None:
        """Solve connection between two planar members"""
        # TODO: Check angle between planes. If same plane orientation, other type of connection.

        # OBB = member2.OBB
        # obbShape = geomUtils.convert_bnd_to_shape(OBB)
        # intersection = geomUtils.find_solid_face_intersection(obbShape, member1.surface)
        # rendering.addDebugShape(intersection)
        # OBB = member2.OBB
        # obbShape = geomUtils.convert_bnd_to_shape(OBB)
        # intersection = geomUtils.find_solid_face_intersection(obbShape, member1.surface)
        # rendering.addDebugShape(intersection)

        # OBB1 = geomUtils.convert_bnd_to_shape(member1.OBB)
        # OBB2 = geomUtils.convert_bnd_to_shape(member2.OBB)

        # int4 = geomUtils.find_solid_face_intersection(OBB1, OBB2)
        # if int4:
        #     rendering.addDebugShape(int4)
        #     print("###########################")

        # int1 = geomUtils.find_face_face_intersection(member1.surface, member2.plane)
        # int2 = geomUtils.find_face_face_intersection(member1.plane, member2.surface)
        # int3 = geomUtils.find_face_face_intersection(member1.plane, member2.plane)

        # if int1: rendering.addDebugShape(int1)
        # if int2: rendering.addDebugShape(int2)
        # if int3: rendering.addDebugShape(int3)

        return None
        ########
        wire = geomUtils.find_face_face_intersection(member1.surface, member2.surface)
        if wire == None:
            logger.warning("No intersection between two planar members!")
        else: return None

        planeface = geomUtils.get_planeface(member1.plane)
        wire = geomUtils.find_face_face_intersection(planeface, member2.surface)
        if wire == None:
            logger.warning("No intersection between plane and surface!")
        else: return None
        
        planeface = geomUtils.get_planeface(member2.plane)
        wire = geomUtils.find_face_face_intersection(member1.surface, planeface)
        if wire == None:
            logger.warning("No intersection between plane and surface!")
        else: return None

        if wire:
            logger.debug(f"Wire: {wire}")
            rendering.addDebugShape(wire)

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
                
            else:
                logger.warning(f"Unknown connection between {type(member1)} and {type(member2)}")
                continue

            if virtualMember == None:
                continue
            self.addMember(virtualMember)

    def get_nodes(self) -> dict:
        """Get all point nodes in model for members."""
        nodes = dict()
        for member in self.members.values():
            member_nodes = member.get_nodes()
            for member_node in member_nodes:
                # nodes.add(member_node)
                nodes[member_node.key] = member_node
            # nodes.extend(member.get_nodes())
        return nodes
    
    def merge_nodes(self):
        """Merge nodes that are close to each other"""
        nodes = self.get_nodes()

        logger.debug(f"Merging {len(nodes)} nodes...")

        for node in nodes.values():
            for other_node in nodes.values():
                if node == other_node:
                    continue
                if node.is_destroyed() or other_node.is_destroyed():
                    continue
                if node.is_equal(other_node):
                    node.merge_nodes(other_node)

        logger.debug(f"Merged {len(nodes)} to {len(self.get_nodes())} nodes...")

class KeyGenerator:
    """Generate unique keys.
    
    Used for node keys.
    """
    def __init__(self):
        self.keys = dict()
        self.counter = 0

    def generate(self, prefix, longKey=None):
        self.counter += 1
        shortKey = f"{prefix}_{self.counter}"
        self.keys[shortKey] = longKey

        return shortKey
    
def make_virtual_member(key1, key2, p1, p2):
    """Very stiff member for connections"""
    distance = geomUtils.distance_between_points(p1, p2)
    
    TOLERANCE = GENERAL_TOLERANCE
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

