"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir, gp_XYZ
from OCC.Core.gp import gp_Pnt, gp_Dir
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line

import numpy as np

"""Converts a bounding box to a box shape."""
def convert_bnd_to_shape(the_box):
    barycenter = the_box.Center()
    x_dir = the_box.XDirection()
    y_dir = the_box.YDirection()
    z_dir = the_box.ZDirection()
    half_x = the_box.XHSize()
    half_y = the_box.YHSize()
    half_z = the_box.ZHSize()

    x_vec = gp_XYZ(x_dir.X(), x_dir.Y(), x_dir.Z())
    y_vec = gp_XYZ(y_dir.X(), y_dir.Y(), y_dir.Z())
    z_vec = gp_XYZ(z_dir.X(), z_dir.Y(), z_dir.Z())
    point = gp_Pnt(barycenter.X(), barycenter.Y(), barycenter.Z())
    axes = gp_Ax2(point, gp_Dir(z_dir), gp_Dir(x_dir))
    axes.SetLocation(
        gp_Pnt(point.XYZ() - x_vec * half_x - y_vec * half_y - z_vec * half_z)
    )
    box = BRepPrimAPI_MakeBox(axes, 2.0 * half_x, 2.0 * half_y, 2.0 * half_z).Shape()
    return box

"""Converts a bounding box to a line on the longest axis"""
def convert_bnd_to_line(the_box):
    barycenter = the_box.Center()
    x_dir = the_box.XDirection()
    y_dir = the_box.YDirection()
    z_dir = the_box.ZDirection()
    half_x = the_box.XHSize()
    half_y = the_box.YHSize()
    half_z = the_box.ZHSize()

    half_sizes = np.array([half_x, half_y, half_z])
    maxIndex = np.argmax(half_sizes)
    
    x_vec = gp_XYZ(x_dir.X(), x_dir.Y(), x_dir.Z())
    y_vec = gp_XYZ(y_dir.X(), y_dir.Y(), y_dir.Z())
    z_vec = gp_XYZ(z_dir.X(), z_dir.Y(), z_dir.Z())

    vecs = np.array([x_vec, y_vec, z_vec])

    point = gp_Pnt(barycenter.X(), barycenter.Y(), barycenter.Z())

    pnt1 = gp_Pnt(point.XYZ() - vecs[maxIndex] * half_sizes[maxIndex])
    pnt2 = gp_Pnt(point.XYZ() + vecs[maxIndex] * half_sizes[maxIndex])

    pt1 = Geom_CartesianPoint(pnt1)
    pt2 = Geom_CartesianPoint(pnt2)

    ais_line = AIS_Line(pt1, pt2)
    return ais_line

"""Converts a bounding box to a plane based on the shortest side"""
def convert_bnd_to_plane(the_box):
    # from OCC.Core.HLRBRep import HLRAlgo_Projector
    return None
