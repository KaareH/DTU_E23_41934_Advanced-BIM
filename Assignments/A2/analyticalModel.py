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

class VirtualMember:
    def __init__(self, key, axis, member1, member2) -> None:
        self.key = key
        self.axis = axis
        self.member1 = member1
        self.member2 = member2


class Beam(StructuralMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID)

        assert geomUtils.is_wire_straight_line(axis)
        self.axis = axis

class Column(StructuralMember):
    def __init__(self, GUID, axis) -> None:
        super().__init__(GUID)

        assert geomUtils.is_wire_straight_line(axis)
        self.axis = axis

class Slab(StructuralMember):
    def __init__(self, GUID) -> None:
        super().__init__(GUID)

class Wall(StructuralMember):
    def __init__(self, GUID) -> None:
        super().__init__(GUID)

class AnalyticalModel:
    def __init__(self) -> None:
        self.members = dict()

    def addMember(self, member) -> None:
        if isinstance(member, StructuralMember):
            assert self.members.get(member.GUID) is None
            self.members[member.GUID] = member
        elif isinstance(member, VirtualMember):
            assert self.members.get(member.key) is None
            self.members[member.key] = member
        else:
            raise TypeError(f"Unknown member type: {type(member)}")
