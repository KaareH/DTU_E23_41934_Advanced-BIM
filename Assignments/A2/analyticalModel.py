"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import geomUtils

class Knot3D:
    def __init__(self) -> None:
        pass

class StructuralMember:
    def __init__(self, GUID) -> None:
        self.GUID = GUID

class PhysicalMember(StructuralMember):
    def __init__(self, GUID) -> None:
        super().__init__(GUID)

class VirtualMember(StructuralMember):
    def __init__(self, key, axis, member1, member2) -> None:
        super().__init__(key)
        self.key = key
        self.axis = axis
        self.member1 = member1
        self.member2 = member2

class AxialMember(PhysicalMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID)
        assert geomUtils.is_wire_straight_line(axis)
        self.axis = axis

class PlanarMember(PhysicalMember):
    def __init__(self, GUID, surface) -> None:
        super().__init__(GUID)
        # Do assert here
        self.surface = surface

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

class AnalyticalModel:
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
