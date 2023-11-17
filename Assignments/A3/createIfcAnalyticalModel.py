"""
Create an IfcStructuralAnalysisModel from an IFC file and write to disk.

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

from OCC.Core.AIS import AIS_TextLabel
from OCC.Core.TCollection import TCollection_AsciiString, TCollection_ExtendedString
from OCC.Core.AIS import AIS_InteractiveContext
from OCC.Core.AIS import AIS_Shape

from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common


from PyNite import FEModel3D
from PyNite.Visualization import Renderer


def runThis(model, outputFileName):
    modelData = ModelData(model)

    # elements = modelData.model.by_type('IfcBeam')
    elements = modelData.model.by_type('IfcBuildingElement')
    elements = {element.GlobalId: element for element in elements}

    aModel = AnalyticalModel()

    for GUID in elements:
        shapes = modelData.shapes[GUID]
        keys = shapes.keys()
        element = modelData.model.by_guid(GUID)
        
        assert 'Body' in keys
        obb = modelData.obbs[GUID]
        body = shapes['Body'].geometry

        
        # Assert that an element doesn't have both Axis and FootPrint
        assert not ('Axis' in keys and 'FootPrint' in keys)

        IfcClass = element.is_a()

        # Beam
        if IfcClass == 'IfcBeam':
            assert 'Axis' in keys

            axis = shapes['Axis'].geometry
            subShapes = get_subShapes(axis)
            assert len(subShapes) == 1
            
            shape = subShapes[0]
            assert is_wire_straight_line(shape)
            wire = shape

            # Axis from ifcopenshell might not even be inside the OBB of the element.
            # Hence not usable at all.
            wire = convert_bnd_to_line(obb, returnWire=True)

            # wire2 = convert_bnd_to_line(obb, returnWire=True)
            # p1a, p2a = geomUtils.get_wire_endpoints(wire)
            # p1b, p2b = geomUtils.get_wire_endpoints(wire2)

            # d1 = np.min([
            #     geomUtils.distance_between_points(p1a, p1b),
            #     geomUtils.distance_between_points(p1a, p2b),
            # ])
            # d2 = np.min([
            #     geomUtils.distance_between_points(p2a, p2b),
            #     geomUtils.distance_between_points(p2a, p1b),
            # ])

            # print(f"d1: {d1}, d2: {d2}")

            member = Beam(GUID, wire)
            # member.wireOBB = wire2

            aModel.addMember(member)
            

        # Column
        elif IfcClass == 'IfcColumn':
            wire = convert_bnd_to_line(obb, returnWire=True)

            member = Column(GUID, wire)
            aModel.addMember(member)

        # Slab
        elif IfcClass == 'IfcSlab':
            # assert 'FootPrint' in keysplaneface = OCC.Core.BRepBuilderAPI.BRepBuilderAPI_MakeFace(plane).Shape()
            plane = geomUtils.convert_bnd_to_plane(obb)
            planeface = OCC.Core.BRepBuilderAPI.BRepBuilderAPI_MakeFace(plane).Shape()
            # Note: commonSurface is taken in the middle of the obb
            commonSurface = BRepAlgoAPI_Common(body, planeface).Shape()
            
            member = Slab(GUID, commonSurface)
            aModel.addMember(member)
            

        # Wall
        elif IfcClass == 'IfcWall':
            pass

        # Plate
        elif IfcClass == 'IfcPlate':
            pass

        elif IfcClass == 'IfcFooting':
            pnt = obb.Center()
            support = Footing(GUID, body, pnt)
            aModel.addMember(support)

        else:
            print(f"Unknown class: {IfcClass}")




    # obbs = {GUID: obbs[GUID] for GUID in elements.keys()}
    obbs = {GUID: modelData.obbs[GUID] for GUID in aModel.members.keys()}
    print(len(obbs))
    common_collisions, element_collisions = find_collisions(obbs)

    collision_pairs = set()

    for key, collisions in element_collisions.items():
        for collision in collisions:
            this_key = tuple(sorted([key, collision]))
            collision_pairs.add(this_key)

    print(len(collision_pairs))

    for collision in collision_pairs:
        key1 = collision[0]
        key2 = collision[1]

        member1 = aModel.members[key1]
        member2 = aModel.members[key2]

        virtualMember = None
        if isinstance(member1, AxialMember) and isinstance(member2, AxialMember):
            wire1 = member1.axis
            wire2 = member2.axis

            p1, p2 = geomUtils.find_closest_points(wire1, wire2)
            virtualMember = make_virtual_member(key1, key2, p1, p2)
            if virtualMember == None:
                continue
        
        # elif ((isinstance(member1, AxialMember) and isinstance(member2, PlanarMember))
        #       or
        #       (isinstance(member2, AxialMember) and isinstance(member1, PlanarMember))):
        #     if isinstance(member1, PlanarMember):
        #         planarMember = member1
        #         axialMember = member2
        #     else:
        #         planarMember = member2
        #         axialMember = member1
            
        #     planarSurface = planarMember.surface
        #     axis = axialMember.axis

        #     p1, p2 = find_closest_points(axis, planarSurface)

        #     continue
        #     # virtualMember = make_virtual_member(key1, key2, p1, p2)
        #     # if not virtualMember:
        #     #     continue
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


        if virtualMember == None:
            continue
        aModel.addMember(virtualMember)

    RenderInWindow(RenderStructuralMembersFunc, modelData=modelData, analyticalModel=aModel)

    print(f"Creating IfcStructuralAnalysisModel...")
    aModel.to_ifc_analysisModel(modelData.model)

    fileName = outputFileName
    print(f"Writing to {fileName}...")
    modelData.model.write(fileName)
    print("Done")

    return aModel


