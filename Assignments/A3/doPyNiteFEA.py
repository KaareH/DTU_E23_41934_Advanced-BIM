"""
Make an analysis using PyNiteFEA

Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import sys
import ifcopenshell

from pyconbim.geomUtils import *
from pyconbim.ifcUtils import *
from pyconbim.rendering import *
from pyconbim.analyticalModel import *
import pyconbim.utils

from PyNite import FEModel3D
from PyNite.Visualization import Renderer

def runThis(aModel):
    class TempNode:
        def __init__(self, pnt, member) -> None:
            self.pnt = pnt
            self.member = member

    temp_nodes = []
    for key, member in aModel.members.items():
        pnts = []
        if isinstance(member, AxialMember):
            p1, p2 = geomUtils.get_wire_endpoints(member.axis)
            pnts.extend([p1, p2])
        elif isinstance(member, VirtualMember):
            p1, p2 = geomUtils.get_wire_endpoints(member.axis)
            pnts.extend([p1, p2])
        elif isinstance(member, Footing):
            p1 = member.pnt
            pnts.extend([p1])
        elif isinstance(member, Slab):
            pass
        else:
            raise Exception(f"Unknown member type: {type(member)}")
        
        for pnt in pnts:
            TempN = TempNode(pnt, member)
            temp_nodes.append(TempN)


    class NewNode:
        def __init__(self, node) -> None:
            self.nodes = [node]
            # self.members = [member]

        def add(self, node):
            self.nodes.append(node)
            # self.members.append(member)

        def get_coords(self):
            # Todo, find average, check if all are the same, of if any are way off
            return self.nodes[0].pnt.Coord()
        
        def get_pnt(self):
            return self.nodes[0].pnt

    new_nodes = []
    for node in temp_nodes:
        pnt = node.pnt
        member = node.member
        for new_node in new_nodes:
            if geomUtils.distance_between_points(new_node.get_pnt(), pnt) < 0.0001:
                new_node.add(node)
                break
        else:
            new_nodes.append(NewNode(node))

    for node in new_nodes:
        for old_node in node.nodes:
            old_node.member.nodes.append(node)

    nodes = new_nodes

    # Create a new finite element model
    model = FEModel3D()
    keyGen = KeyGenerator()

    VIRT_F = 1_000_000.0
    Z_LOAD = -1.1
    PNT_S = 10.0


    # Define a material
    E = 2000.0       # Modulus of elasticity (ksi)
    G = 1000.0       # Shear modulus of elasticity (ksi)
    nu = 0.3        # Poisson's ratio
    rho = 2.836e-4  # Density (kci)
    model.add_material('Steel', E, G, nu, rho)
    model.add_material('VirtStiff', VIRT_F*E, VIRT_F*G, nu, rho)


    print(f"Node count: {len(nodes)}")
    for i, node in enumerate(nodes):
        key = keyGen.generate('N', f"None-{i}")
        coords = node.get_coords()
        # N_key = model.add_node(key, PNT_S*coords[0], PNT_S*coords[1], PNT_S*coords[2])
        N_key = model.add_node(key, float(PNT_S*coords[0]), float(PNT_S*coords[1]), float(PNT_S*coords[2]))
        print(f"Coords: {coords}")
        node.key = N_key
        print(N_key)
        model.def_support(N_key, True, True, True, True, True, True)


    for key, member in aModel.members.items():
        if isinstance(member, AxialMember):
            # wire = member.axis
            # p1, p2 = geomUtils.get_wire_endpoints(wire)

            # N1_key = model.add_node(keyGen.generate('N', ('N', *key, '_1')), PNT_S*p1.X(), PNT_S*p1.Y(), PNT_S*p1.Z())
            # N2_key = model.add_node(keyGen.generate('N', ('N', *key, '_2')), PNT_S*p2.X(), PNT_S*p2.Y(), PNT_S*p2.Z())

            # Temporary
            # model.def_support(N1_key, True, True, True, True, True, True)
            # model.def_support(N2_key, True, True, True, True, True, True)

            assert len(member.nodes) == 2
            N1_key = member.nodes[0].key
            N2_key = member.nodes[1].key

            M_key = model.add_member(keyGen.generate('M', ('M', key)), N1_key, N2_key, 'Steel', 100, 150, 250, 2000)        
            model.add_member_dist_load(M_key, 'FZ', Z_LOAD, Z_LOAD)

            
        elif isinstance(member, VirtualMember):
            # wire = member.axis
            # p1, p2 = geomUtils.get_wire_endpoints(wire)
            # # virt, key1, key2 = key

            # N1_key = model.add_node(keyGen.generate('N', ('N', *key, '_1')), PNT_S*p1.X(), PNT_S*p1.Y(), PNT_S*p1.Z())
            # N2_key = model.add_node(keyGen.generate('N', ('N', *key, '_2')), PNT_S*p2.X(), PNT_S*p2.Y(), PNT_S*p2.Z())

            # Temporary
            # model.def_support(N1_key, True, True, True, True, True, True)
            # model.def_support(N2_key, True, True, True, True, True, True)

            assert len(member.nodes) == 2
            N1_key = member.nodes[0].key
            N2_key = member.nodes[1].key

            M_key = model.add_member(keyGen.generate('M', ('M', key)), N1_key, N2_key, 'VirtStiff', 100, 150, 250, 2000)
            # model.add_member_dist_load(M_key, 'Fy', Y_LOAD, Y_LOAD)
        
        elif isinstance(member, Footing):
            # p1 = member.pnt
            # N1_key = model.add_node(keyGen.generate('NS', ('NS', *key, '_1')), PNT_S*p1.X(), PNT_S*p1.Y(), PNT_S*p1.Z())
            assert len(member.nodes) == 1
            N1_key = member.nodes[0].key

            model.def_support(N1_key, True, True, True, True, True, True)
        elif isinstance(member, Slab):
            pass
            
        else:
            raise Exception(f"Unknown member type: {type(member)}")
        

    model.analyze()


    renderer = Renderer(model)
    # renderer.annotation_size = 0.05
    renderer.annotation_size = 0.05
    renderer.deformed_shape = True
    renderer.deformed_scale = 10.0
    renderer.render_loads = True
    renderer.render_model()



