"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import pytest

# from PyConBIM import geomUtils
from pyconbim import geomUtils
# from OCC.Core.gp import gp_Pnt

# def test_distance_between_points():
#     p1 = gp_Pnt(0.0, 0.0, 0.0)
#     p2 = gp_Pnt(1.0, 1.0, 1.0)

#     distance = geomUtils.distance_between_points(p1, p2)

#     expected_distance = 1.7320508075688772
#     assert abs(distance - expected_distance) < 0.001

#     wrong_distance = 1.8320508075688772
#     assert not abs(distance - wrong_distance) < 0.001

def test_sampleUtil():
    assert geomUtils.exampleFunc(1,2) == 3
