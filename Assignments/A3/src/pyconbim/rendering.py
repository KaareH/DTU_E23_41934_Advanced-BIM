"""
Rendering functions

Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

from deprecated.sphinx import deprecated
import ifcopenshell.util

from OCC.Display.SimpleGui import init_display
from OCC.Display.WebGl.jupyter_renderer import JupyterRenderer, format_color
from OCC.Core.Graphic3d import Graphic3d_BufferType
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Display.OCCViewer import Viewer3d
from OCC.Core.Bnd import Bnd_Box
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Core.gp import gp_Pnt, gp_Ax2, gp_Dir, gp_XYZ
from OCC.Core.gp import gp_Pnt, gp_Dir
from OCC.Core.Geom import Geom_CartesianPoint
from OCC.Core.AIS import AIS_Line
from OCC.Core.Bnd import Bnd_OBB
from OCC.Core.BRepBndLib import brepbndlib
from OCC.Core.AIS import AIS_InteractiveContext
from OCC.Core.AIS import AIS_Shape
from OCC.Core.AIS import AIS_TextLabel
from OCC.Core.TCollection import TCollection_AsciiString, TCollection_ExtendedString
import OCC.Core.BRepPrimAPI
import OCC.Core.BRepTools

from PIL import Image

from pyconbim.analyticalModel import *
import pyconbim.geomUtils as geomUtils

RED = Quantity_Color(1.0, 0.0, 0.0, Quantity_TOC_RGB)
GREEN = Quantity_Color(0.0, 1.0, 0.0, Quantity_TOC_RGB)
BLUE = Quantity_Color(0.0, 0.0, 1.0, Quantity_TOC_RGB)
MAGENTA = Quantity_Color(1.0, 0.0, 1.0, Quantity_TOC_RGB)
BLACK = Quantity_Color(0.0, 0.0, 0.0, Quantity_TOC_RGB)
GREY = Quantity_Color(0.5, 0.5, 0.5, Quantity_TOC_RGB)
YELLOW = Quantity_Color(0.0, 1.0, 1.0, Quantity_TOC_RGB)

def quickJupyterRender(elements_render, settings, my_renderer = None):
    """Interactive renderer in Jupyter notebook"""

    if my_renderer is None:
        my_renderer = JupyterRenderer(size=(700, 700))

    for element in elements_render:
        if element.Representation is not None:
            body = ifcopenshell.util.representation.get_representation(element, "Model", "Body")
            body_repr = ifcopenshell.util.representation.resolve_representation(body)
            pdct_shape = ifcopenshell.geom.create_shape(settings, inst=element, repr=body_repr)

            r,g,b,alpha = pdct_shape.styles[0] # the shape color

            color = format_color(int(abs(r)*255), int(abs(g)*255), int(abs(b)*255))
            my_renderer.DisplayShape(pdct_shape.geometry, shape_color = color, transparency=True, opacity=alpha)
        
    return my_renderer

def RenderImage(renderFunc, img_size=(1024, 768), **args):
    """Render static image for display in notebok"""

    offscreen_renderer = Viewer3d()
    offscreen_renderer.Create()
    offscreen_renderer.SetModeShaded()

    # offscreen_renderer.View.SetUp(0, 0, -1)

    # Do the rendering
    renderFunc(offscreen_renderer, **args)

    # Get image data
    img_bytes = offscreen_renderer.GetImageData(
        *img_size,
        Graphic3d_BufferType.Graphic3d_BT_RGB,
    )

    offscreen_renderer.SetSize(*img_size)
    # offscreen_renderer.View.Dump(f"./capture_jpeg.jpeg")

    img = Image.frombytes('RGB', img_size, img_bytes)
    img = img.transpose(Image.Transpose.FLIP_TOP_BOTTOM)

    return img 

def RenderInWindow(renderFunc, window_size=(1500, 1000), **args):
    """Interactive renderer in stand alone window"""

    occ_display, start_display, add_menu, add_function_to_menu = init_display(size=window_size)

    try:
        # Do the rendering
        renderFunc(occ_display, **args)

    except Exception as e:
        print(f"Exception!: {e}")

    finally:
        start_display()

def SimpleRenderFunc(renderer, **args):
    """Render a bunch of shapes"""

    shapes = args['shapes']

    for i, shape in enumerate(shapes):
        to_update = i % 50 == 0

        try:
            renderer.DisplayShape(
                shape,
                update=to_update,
            )

        except Exception as e:
                print(f"Error! {e}")

    renderer.FitAll()

@deprecated(reason=
            "Use processGeometry and other renderFunc instead",
            version="0.0.1",
)
def ElementsRenderFunc(renderer, **args):
    """Render a bunch of IFC elements. Only renders body"""

    elements = args['elements']

    if args.get('settings'):
        settings = args['settings']
    else:
        settings = ifcopenshell.geom.settings()
        settings.set(settings.USE_PYTHON_OPENCASCADE, True)

    for i, (GUID, element) in enumerate(elements.items()):
        to_update = i % 50 == 0

        try:
            if element.Representation is not None:
                body = ifcopenshell.util.representation.get_representation(element, "Model", "Body")
                body_repr = ifcopenshell.util.representation.resolve_representation(body)
                pdct_shape = ifcopenshell.geom.create_shape(settings, inst=element, repr=body_repr)

                r,g,b,alpha = pdct_shape.styles[0] # the shape color
                color = Quantity_Color(abs(r), abs(g), abs(b), Quantity_TOC_RGB)


                renderer.DisplayShape(
                    pdct_shape.geometry,
                    color = color,
                    transparency=abs(1 - alpha),
                    update=to_update,
                )

        except Exception as e:
                print(f"Error! {e}")

    renderer.FitAll()

def FitToShape(occ_display, shape, enlarge=0.02):
    """Fit and zoom renderer camera to a specific object in the scene"""

    bbox = Bnd_Box()
    brepbndlib.Add(shape, bbox)
    
    bbox.Enlarge(enlarge)

    diag = bbox.SquareExtent() ** 0.5
    occ_display.View.FitAll(bbox, diag)

    bboxShp = BRepPrimAPI_MakeBox(bbox.CornerMin(), bbox.CornerMax()).Shape()

    return bbox, bboxShp

def RenderStructuralMembersFunc(renderer, **args):
    """Render structural members"""

    try:
        modelData = args['modelData']
        aModel = args['analyticalModel']
        members = aModel.members
    except Exception as e:
        print(f"Error! {e}")
        return
    
    try:
        settings = args['settings']
    except Exception as e:
        settings = {}

    if settings.get('render_bodies') == None:
        settings['render_bodies'] = True

    WIRE_SIZE = 10.0

    def renderLabel(text, GUID, color=BLACK):
        """GUID for OBB lookup"""
        # TODO: Fix this, crashes without error 

        # Render label
        # obb = modelData.obbs[GUID]
        # textLabel = AIS_TextLabel()
        # textLabel.SetPosition(gp_Pnt(obb.Center()))
        # textLabel.SetText(TCollection_ExtendedString(text))
        # textLabel.SetColor(color)

        # renderer.Context.Display(textLabel, False)
        return

    def renderBeam(member):
        # Render axis
        axis = member.axis
        shape = axis

        ais_shp = AIS_Shape(shape)
        ais_shp.SetWidth(WIRE_SIZE)
        ais_shp.SetColor(MAGENTA)
        ais_context.Display(ais_shp, False)

        # Render points
        wire = shape

        p1, p2 = geomUtils.get_wire_endpoints(wire)

        renderer.DisplayShape(
            p1,
            # color=color,
        )
        renderer.DisplayShape(
            p2,
            # color=color,
        )
        renderLabel("Beam", member.GUID)
        return

    def renderColumn(member):
        wire = member.axis

        # Render axis
        shape = wire
        ais_shp = AIS_Shape(shape)
        ais_shp.SetWidth(WIRE_SIZE)
        ais_shp.SetColor(BLUE)
        ais_context.Display(ais_shp, False)

        # Render points
        p1, p2 = geomUtils.get_wire_endpoints(wire)
        renderer.DisplayShape(
            p1,
            color=BLUE,
        )
        renderer.DisplayShape(
            p2,
            color=BLUE,
        )
        renderLabel("Column", member.GUID)
        return

    def renderFooting(member):
        body = member.body
        renderer.DisplayShape(
            body,
            color=BLACK,
            transparency=transparency,
            # update=to_update,
        )
        renderer.DisplayShape(
            member.pnt,
            color=BLACK,
            transparency=transparency,
            # update=to_update,
        )
        renderLabel("Footing", member.GUID)
        return
    
    def renderSlab(member):
        shape = member.surface
        renderer.DisplayShape(
            shape,
            color=RED,
            transparency=0.8,
            update=to_update,
        )
        renderLabel("Slab", member.GUID)
        return
    
    def renderWall(member):
        shape = member.surface
        renderer.DisplayShape(
            shape,
            color=YELLOW,
            transparency=0.8,
            update=to_update,
        )
        renderLabel("Wall", member.GUID)
        return
    
    def renderVirtualMember(member):
        wire = member.axis

        # Render axis
        shape = wire
        ais_shp = AIS_Shape(shape)
        ais_shp.SetWidth(WIRE_SIZE)
        ais_shp.SetColor(GREEN)
        ais_context.Display(ais_shp, False)
        # Render points
        p1, p2 = geomUtils.get_wire_endpoints(wire)
        renderer.DisplayShape(
            p1,
            color=MAGENTA,
        )
        renderer.DisplayShape(
            p2,
            color=MAGENTA,
        )
        return

    ais_context = renderer.GetContext()

    #################
    # Render bodies #
    #################
    if settings.get('render_bodies'):
        transparency=0.7
        if settings.get('bodies_transparency'):
            transparency = settings['bodies_transparency']

        for i,  (GUID, member) in enumerate(members.items()):
            to_update = i % 50 == 0
            try:
                if type(member) in [Beam, Column]:
                    body = modelData.shapes[GUID]['Body'].geometry
                    renderer.DisplayShape(
                        body,
                        color=GREY,
                        transparency=transparency,
                    )
            except Exception as e:
                print(e)

    #############################
    # Render structural members #
    #############################

    transparency = 0.8
    # Idea: have render code be part of each Structural Members own class
    for i,  (GUID, member) in enumerate(members.items()):
        to_update = i % 50 == 0

        transparency = 0.8
        try:
            if type(member) == Beam:
                renderBeam(member)
            elif type(member) == Column:
                renderColumn(member)
            elif type(member) == Footing:
                renderFooting(member)
            elif type(member) == VirtualMember:
                renderVirtualMember(member)
            elif type(member) == Slab:
                renderSlab(member)
            elif type(member) == Wall:
                renderWall(member)
            else:
                pass

        except Exception as e:
                print(f"Error! {e}")
                

    renderer.FitAll()
    return
