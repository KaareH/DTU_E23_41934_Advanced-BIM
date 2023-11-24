"""
Geometric utilities

Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import numpy as np

from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir, gp_XYZ
from OCC.Core.gp import gp_Pnt, gp_Dir
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line
from OCC.Core.Bnd import Bnd_OBB
from OCC.Core.BRepBndLib import brepbndlib
import OCC.Core.BRepPrimAPI
import OCC.Core.BRepTools
from OCC.Core.BRepTools import breptools
from OCC.Core.gp import gp_Vec, gp_Dir
from OCC.Core.TopoDS import TopoDS_Vertex, TopoDS_Wire
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.BRep import BRep_Tool
from OCC.Core.BRepTools import BRepTools_WireExplorer
from OCC.Core.GeomAbs import GeomAbs_CurveType
from OCC.Core.TopExp import topexp_FirstVertex
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeWire, BRepBuilderAPI_MakeEdge
from OCC.Core.GeomAPI import GeomAPI_Interpolate
from OCC.Core.TColgp import TColgp_Array1OfPnt, TColgp_HArray1OfPnt
from OCC.Core.gp import gp_Pnt
from OCC.Core.TopoDS import TopoDS_Iterator, TopoDS_ListOfShape, TopoDS_TWire
from OCC.Core.TopExp import topexp_Vertices
from OCC.Core.BRepExtrema import BRepExtrema_DistShapeShape
from OCC.Core.gp import gp_Pln
from OCC.Core.gp import gp_Ax3
from OCC.Core.TopExp import topexp
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_FACE
from OCC.Core.BRep import BRep_Tool
from OCC.Core.gp import gp_Pnt, gp_Pln, gp_Dir, gp_Ax3
from OCC.Core.BRepAdaptor import BRepAdaptor_Surface
from OCC.Core.TopExp import TopExp_Explorer
from OCC.Core.TopAbs import TopAbs_EDGE, TopAbs_WIRE, TopAbs_FACE
from OCC.Core.BRepAdaptor import BRepAdaptor_Curve
from OCC.Core.TopoDS import topods, TopoDS_Face, TopoDS_Shape
from OCC.Core.gp import gp_Pnt
from OCC.Core.BRepAlgoAPI import BRepAlgoAPI_Common
from OCC.Core.TopoDS import topods
from OCC.Core.TopoDS import TopoDS_Compound, TopoDS_Builder
from OCC.Core.gp import gp_Trsf, gp_Mat
from OCC.Core.TopLoc import TopLoc_Location

def convert_bnd_to_shape(the_box: Bnd_OBB):
    """Converts a bounding box to a box shape."""
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

def convert_bnd_to_line(the_box: Bnd_OBB, returnWire=False) -> AIS_Line:
    """Converts a bounding box to a line on the longest axis"""
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

    if returnWire:
        wire = make_wire_from_points([pnt1, pnt2])
        return wire
    
    pt1 = Geom_CartesianPoint(pnt1)
    pt2 = Geom_CartesianPoint(pnt2)

    ais_line = AIS_Line(pt1, pt2)

    return ais_line

# def convert_bnd_to_plane(the_box):
#     """Converts a bounding box to a plane based on the shortest side"""
#     # from OCC.Core.HLRBRep import HLRAlgo_Projector

def convert_bnd_to_plane(the_box: Bnd_OBB) -> gp_Pln:
    """Converts a bounding box to a plane."""
    barycenter = the_box.Center()
    x_dir = the_box.XDirection()
    y_dir = the_box.YDirection()
    z_dir = the_box.ZDirection()
    half_x = the_box.XHSize()
    half_y = the_box.YHSize()
    half_z = the_box.ZHSize()

    half_sizes = np.array([half_x, half_y, half_z])
    maxIndex = np.argmax(half_sizes)
    minIndex = np.argmin(half_sizes)
    middleIndex = 3 - maxIndex - minIndex
    
    x_vec = gp_XYZ(x_dir.X(), x_dir.Y(), x_dir.Z())
    y_vec = gp_XYZ(y_dir.X(), y_dir.Y(), y_dir.Z())
    z_vec = gp_XYZ(z_dir.X(), z_dir.Y(), z_dir.Z())

    vecs = np.array([x_vec, y_vec, z_vec])
    dirs = np.array([x_dir, y_dir, z_dir])

    point = gp_Pnt(barycenter.X(), barycenter.Y(), barycenter.Z())


    axes = gp_Ax2(point, gp_Dir(dirs[minIndex]), gp_Dir(dirs[middleIndex]))
    # axes = gp_Ax2(point, gp_Dir(dirs[maxIndex]), gp_Dir(dirs[middleIndex]))
    # axes.SetLocation(
    #     gp_Pnt(point.XYZ() - x_vec * half_x - y_vec * half_y - z_vec * half_z)
    # )
    
    axes = gp_Ax3(axes)

    plane = gp_Pln(axes)

    x_dir = gp_Dir(x_dir)
    y_dir = gp_Dir(y_dir)
    z_dir = gp_Dir(z_dir)

    return plane#, axes, z_dir

def find_collisions(elements_obb, enlargement=0.001):
    """Retreive a list of OBBs that collide with each other"""
    common_collisions = set()
    element_collisions = dict()

    for key, obb in elements_obb.items():
        collides_with = list()
        collisions = list()
        obb_enlarged = Bnd_OBB()
        obb_enlarged.Add(obb)
        obb_enlarged.Enlarge(enlargement)

        for key2, obb2 in elements_obb.items():
            # collides = not obb.IsOut(obb2)
            # Ide! Tjek både enlarged og ikke enlarged. Notify hvis de ikke siger det samme....
            collides = not obb_enlarged.IsOut(obb2)

            if collides:
                collides_with.append(key2)
        
            if key == key2: continue
            if collides:
                collisions.append(key2)
        
        element_collisions[key] = collisions

        collides_with.sort()
        common_collisions.add(tuple(collides_with))

    return common_collisions, element_collisions

def get_elementsOBB(elements_shape):
    """Get a bunch of OBBs from IFC elements"""
    elements_obb = dict()

    for GUID, pdct_shape in elements_shape.items():
        elmShape = pdct_shape.geometry
        obb = get_OBB(elmShape)
        
        # Enlarge
        # obb.Enlarge(0.01)

        elements_obb[GUID] = obb

    return elements_obb

def get_OBB(elmShape) -> Bnd_OBB:
    """Return OBB for a shape"""
    obb = Bnd_OBB()
    brepbndlib.AddOBB(elmShape, obb, True, True, True)

    return obb

def elongateOBB(OBB: Bnd_OBB, mulF=1.0, addF=0.0) -> Bnd_OBB:
    """Elongate an OBB in its longest direction"""
    obb = Bnd_OBB()
    obb.Add(OBB)

    half_x = obb.XHSize()
    half_y = obb.YHSize()
    half_z = obb.ZHSize()

    half_sizes = np.array([half_x, half_y, half_z])
    maxIndex = np.argmax(half_sizes)

    if maxIndex == 0:
        obb.SetXComponent(gp_Dir(obb.XDirection()), obb.XHSize()*mulF + addF)
    if maxIndex == 1:
        obb.SetYComponent(gp_Dir(obb.YDirection()), obb.YHSize()*mulF + addF)
    if maxIndex == 2:
        obb.SetZComponent(gp_Dir(obb.ZDirection()), obb.ZHSize()*mulF + addF)

    return obb

def is_wire_straight_line(wire: TopoDS_Wire, angularTolearance=0.01) -> bool:
    """Check if a TopoDS_Wire is a straight line"""
    iter_edge = BRepTools_WireExplorer(wire)
    first_edge = iter_edge.Current()
    first_curve = BRepAdaptor_Curve(first_edge)
    first_vec = gp_Vec(first_curve.Value(first_curve.FirstParameter()),
                       first_curve.Value(first_curve.LastParameter()))

    while iter_edge.More():
        edge = iter_edge.Current()
        curve = BRepAdaptor_Curve(edge)
        
        curveType = GeomAbs_CurveType(curve.GetType())
        
        if not curveType == GeomAbs_CurveType.GeomAbs_Line:
            return False

        start_vertex = topexp.FirstVertex(edge)
        start_point = BRep_Tool.Pnt(start_vertex)
        end_point = curve.Value(curve.LastParameter())
        vec = gp_Vec(start_point, end_point)
        
        # angularTolearance = gp_Dir().AngularTolerance()
        # print(vec.Angle(first_vec))
        if vec.Angle(first_vec) > angularTolearance:
            return False
        iter_edge.Next()
    return True

def make_wire_from_points(points) -> TopoDS_Wire:
    """Make a TopoDS_Wire from a list of points"""
    wire_builder = BRepBuilderAPI_MakeWire()
    for i in range(len(points)-1):
        edge_builder = BRepBuilderAPI_MakeEdge(points[i], points[i+1])
        wire_builder.Add(edge_builder.Edge())
    return wire_builder.Wire()

def make_wire_from_bspline(bspline_curve):
    """Make a TopoDS_Wire from a bspline curve"""
    edge_builder = BRepBuilderAPI_MakeEdge(bspline_curve)
    wire_builder = BRepBuilderAPI_MakeWire()
    wire_builder.Add(edge_builder.Edge())
    return wire_builder.Wire()

def make_bspline_from_points(points):
    """Make a bspline curve from a list of gp_Pnt"""
    array_of_points = TColgp_HArray1OfPnt(1, len(points))
    for i, point in enumerate(points):
        array_of_points.SetValue(i+1, point)

    interpolator = GeomAPI_Interpolate(array_of_points, False, 1.0e-6)

    interpolator.Perform()

    if interpolator.IsDone():
        curve = interpolator.Curve()
        return curve
    
    raise Exception("Could not interpolate points")

def get_subShapes(shape):
    """Get all subshapes of a TopoDS_Compund"""
    subShapes = list()

    ds_iter = TopoDS_Iterator(shape)
    while ds_iter.More():
        subShape = ds_iter.Value()
        subShapes.append(subShape)
        
        ds_iter.Next()
    
    return subShapes
    
def get_wire_endpoints(wire: TopoDS_Wire):
    """Get endpoints of a wire"""
    v1 = TopoDS_Vertex()
    v2 = TopoDS_Vertex()
    topexp.Vertices(wire, v1, v2)

    p1 = BRep_Tool().Pnt(TopoDS_Vertex(v1))
    p2 = BRep_Tool().Pnt(TopoDS_Vertex(v2))

    return p1, p2

def find_closest_points(wire1: TopoDS_Wire, wire2: TopoDS_Wire):
    """Return the closest points on two wires"""
    dist_shape_shape = BRepExtrema_DistShapeShape(wire1, wire2)
    dist_shape_shape.Perform()
    return dist_shape_shape.PointOnShape1(1), dist_shape_shape.PointOnShape2(1)

def distance_between_points(p1: gp_Pnt, p2: gp_Pnt) -> float:
    """Calculate distance between two points"""
    return p1.Distance(p2)

def find_solid_face_intersection(shape, face: TopoDS_Face):
    """Compute the intersection between a solid and a face. Return a TopoDS_Face"""
    # Create a compound to store the result
    result_compound = TopoDS_Compound()
    builder = TopoDS_Builder()
    builder.MakeCompound(result_compound)

    # Perform the intersection
    common_algo = BRepAlgoAPI_Common(shape, face)
    common_algo.Build()

    # Get the resulting shape
    result_shape = common_algo.Shape()

    # Add the resulting shape to the compound
    builder.Add(result_compound, result_shape)

    # Extract faces from the compound
    face_list = []
    face_exp = TopExp_Explorer(result_compound, TopAbs_FACE)
    while face_exp.More():
        # face_list.append(topods_Face(face_exp.Current()))
        face_list.append(topods.Face(face_exp.Current()))
        face_exp.Next()

    # Return the first face (assuming there's only one face in the result)
    if face_list:
        # assert len(face_list) == 1
        if len(face_list) != 1:
            print(f"Warning: More than one face in result: {len(face_list)}")
        return face_list[0]
    else:
        return None

def deconstruct_face(face: TopoDS_Face):
    """
    Deconstruct a TopoDS_Face into a surface and a list of wires.
    Attempts to find the outer wire and inner wires (for holes).
    """
    face_surface = BRepAdaptor_Surface(face)
    outer_wire = breptools.OuterWire(face)

    inner_wires = []
    wire_exp = TopExp_Explorer(face, TopAbs_WIRE)
    while wire_exp.More():
        wire = topods.Wire(wire_exp.Current())
        if wire == outer_wire:
            pass
        else:
            inner_wires.append(wire)

        wire_exp.Next()

    return face_surface, outer_wire, inner_wires

def transform_to_local(shape: TopoDS_Shape, scaleFactor=1.0) -> (TopoDS_Shape, gp_Trsf):
    """
    Transform a shape to local coordinates. Origin is center of OBB.
    
    Returns:
        shape: TopoDS_Shape - Transformed shape
        transformation: gp_Trsf - Transformation from global to local coordinates
    """

    # Move shape to orign with local transformation
    OBB = get_OBB(shape)
    transformation = gp_Trsf()
    transformation.SetTransformation(OBB.Position())
    transformation.SetScaleFactor(scaleFactor)
    location = TopLoc_Location(transformation)
    # shape.Location(location, False) <--- Don't use this. Otherwise it will not be copied
    shape = shape.Located(location, False)

    return shape, transformation

def adaptive_wire_to_polyline(wire: TopoDS_Wire, face: TopoDS_Face, min_num_samples=10, max_num_samples=100) -> [gp_Pnt]:
    """
    Convert a TopoDS_Wire to a polyline. The polyline will be a list of gp_Pnt.

    Lines will only be added as the wire vertices. Other curves will be sampled.

    TODO: Add support for arcs and other curves.
    TODO: Make num_samples adaptive based on curvature.
    """
    polyline_points = []

    curve_adaptor = BRepAdaptor_Curve()
    explorer = BRepTools_WireExplorer(wire, face)
    while explorer.More():
        edge = explorer.Current()
        vertex = explorer.CurrentVertex()
        explorer.Next()

        curve_adaptor.Initialize(edge)
        curve_type = GeomAbs_CurveType(curve_adaptor.GetType())
        
        # Line
        if curve_type == GeomAbs_CurveType.GeomAbs_Line:
            line = curve_adaptor.Line()
            num_samples = 2
            pnt = BRep_Tool.Pnt(vertex)
            polyline_points.append(pnt)
            continue

        # Cirlce
        elif curve_type == GeomAbs_CurveType.GeomAbs_Circle:
            circle = curve_adaptor.Circle()
            num_samples = 10

        # Other
        else:
            print("Other type!!!!!!!")
            num_samples = 10
            # assert False

        # Get first and last parameter for current edge
        A_u = curve_adaptor.FirstParameter()
        B_u = curve_adaptor.LastParameter()
        # print("u = ", A_u, B_u)

        A_P= gp_Pnt()
        A_D1 = gp_Vec()
        A_D2 = gp_Vec()
        B_P = gp_Pnt()
        B_D1 = gp_Vec()
        B_D2 = gp_Vec()

        curve_adaptor.D2(A_u, A_P, A_D1, A_D2)
        curve_adaptor.D2(B_u, B_P, B_D1, B_D2)

        is_same = A_D1 != B_D1
        # print("Is same", is_same)
        is_curved = not is_same

        # Sample points along the curve and add them to the polyline
        for u in np.linspace(A_u, B_u, num_samples):
            pnt = curve_adaptor.Value(u)
            polyline_points.append(pnt)

    return polyline_points
