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

import pyconbim.geomUtils as geomUtils

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
        super().to_ifc_structuralMember(model)

        # TODO: Add representaiton
        curveMember = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcStructuralCurveMember")

        return curveMember

class PlanarMember(PhysicalMember):
    """Abstract class for planar members"""

    def __init__(self, GUID, surface) -> None:
        super().__init__(GUID)
        # Do assert here
        self.surface = surface
    
    def to_ifc_structuralMember(self, model):
        """Return IfcStructuralSurfaceMember"""
        super().to_ifc_structuralMember(model)

        # TODO: Add representaiton
        surfaceMember = ifcopenshell.api.run("root.create_entity", model, ifc_class="IfcStructuralSurfaceMember")

        return surfaceMember

class Beam(AxialMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID, axis)

class Column(AxialMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID, axis)

class Slab(PlanarMember):
    def __init__(self, GUID, surface) -> None:
        super().__init__(GUID, surface)

class Wall(PlanarMember):
    def __init__(self, GUID, surface) -> None:
        super().__init__(GUID, surface)

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

        analysisModel = run("root.create_entity", model, ifc_class="IfcStructuralAnalysisModel")
        # run("aggregate.assign_object", model, relating_object=building, product=analysisModel)
        
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

