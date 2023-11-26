"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import pytest

from pyconbim.ifcUtils import load_models, ModelData
from pyconbim.geomUtils import (get_subShapes, is_wire_straight_line,
    convert_bnd_to_line, get_wire_endpoints, distance_between_points)
from pyconbim.analyticalModel import Beam, ElementData

def test_beam_length():
    models = load_models(model_dir="./models",
                         models={
                             'beam-extruded': 'beam-extruded-solid.ifc',
                             'beam-revolved': 'beam-revolved-solid.ifc',})
    
    modelData = ModelData(models['beam-extruded'])

    shapes = [shape['Body'].geometry for _, shape in modelData.shapes.items()]

    beams = modelData.model.by_type('IfcBeam')
    assert len(beams) == 1
    beam = beams[0]

    GUID = beam.GlobalId
    shapes = modelData.shapes[GUID]
    keys = shapes.keys()
    
    obb = modelData.obbs[GUID]

    assert 'Axis' in keys

    axis = shapes['Axis'].geometry
    subShapes = get_subShapes(axis)
    assert len(subShapes) == 1
    
    shape = subShapes[0]
    assert is_wire_straight_line(shape)
    wire = convert_bnd_to_line(obb, returnWire=True)

    elementData = ElementData(
                GUID = GUID,
                element = beam,
                shapes = shapes,
                keys = keys,
                OBB = obb,
                body = shapes['Body'].geometry,
            )

    member = Beam(elementData)

    wire = member.axis
    p1, p2 = get_wire_endpoints(wire)

    expected_distance = 10.0
    distance = distance_between_points(p1, p2)
    print(f"Distance: {distance}")
    assert abs(distance - expected_distance) < 0.1