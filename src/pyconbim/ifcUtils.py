# Kaare G. S. Hansen, s214282 - DTU
# 41934 - Advanced BIM, E23

""" Ifc utilities.

Utilities for working with IFC-models.
"""

import os
import sys
import multiprocessing
from loguru import logger
from deprecated.sphinx import deprecated

import ifcopenshell
import ifcopenshell.util.placement
import ifcopenshell.geom
import ifcopenshell.util.shape
import ifcopenshell.util.selector
from OCC.Core.gp import gp_Pnt

import pyconbim.geomUtils as geomUtils

class ModelData:
    def __init__(self, model) -> None:
        self.model = model

        # Preprocessing data
        self.GUIDS_ignore = set()
        self.GUIDS_enlarge = dict()
        self.GUIDS_foundation = set()

        shapeData, tree, unit_magnitude, unit_name = processGeometry(model)

        self.shapes = shapeData
        self.tree = tree
        self.unit_magnitude = unit_magnitude
        self.unit_name = unit_name

        elements_shape = {GUID: shapeData[GUID] for GUID in shapeData.keys()}
        elements_bodies = dict()
        for GUID, shapes in elements_shape.items():
            if shapes.get('Body'):
                elements_bodies[GUID] = shapes['Body']

        self.obbs = geomUtils.get_elementsOBB(elements_bodies)
    
    def get_structuralMembers(self):
        """ Get filtered structural members in model.
        Returned elements are filtered with respect to preprocessing.
        """
        load_bearing = getLoadBearing(self.model)
        load_bearing = {element.GlobalId for element in load_bearing}

        elements = load_bearing

        for GUID in self.GUIDS_foundation:
            elements.add(GUID)

        # Ignore should be done last
        for GUID in self.GUIDS_ignore:
            elements.remove(GUID)
        
        elements = {GUID: self.model.by_guid(GUID) for GUID in elements}
        return elements


def load_models(model_dir, models):
    """Load multiple models"""

    model_paths = dict()
    for key, fileName in models.items():
        model_paths[key] = os.path.join(model_dir, fileName)

    models = dict()
    for key, model_path in model_paths.items():
        logger.info(f"File path, {key}: {model_path}")
        model = ifcopenshell.open(model_path)
        logger.info(f"Model schema: {model.schema}\n")
        models[key] = model
    
    return models

def getLoadBearing(model):
    """Get all load bearing elements in model"""

    load_bearing = list(ifcopenshell.util.selector.filter_elements(model,
    "IfcBuildingElement, /Pset_.*Common/.LoadBearing=TRUE"))

    unique_types = set(el.get_info()['type'] for el in load_bearing)

    logger.info(f"Number of load-bearing elements: {len(load_bearing)}")
    logger.info(f"Unique types of loadbearing elements:\n {unique_types}")

    return load_bearing

def processGeometry(model):
    """Process all geometry in model"""

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)  # tells ifcopenshell to use pythonocc

    #################
    # Extra options #
    #################

    settings.set(settings.USE_BREP_DATA,True)
    settings.set(settings.SEW_SHELLS,True)
    # settings.set(settings.USE_WORLD_COORDS,True)
    settings.set(settings.INCLUDE_CURVES, True)
    settings.set(settings.EDGE_ARROWS, True)
    settings.set(settings.APPLY_LAYERSETS, True)
    settings.set(settings.VALIDATE_QUANTITIES, True)
    settings.set(settings.APPLY_DEFAULT_MATERIALS, True)

    CORE_COUNT = multiprocessing.cpu_count()
    tree = ifcopenshell.geom.tree()
    iterator = ifcopenshell.geom.iterator(settings, model, CORE_COUNT)

    logger.info(f"Beginning processing with {CORE_COUNT} threads...")
    contexts = set()
    shapeData = dict()

    totalCount = 0
    i = 0
    if iterator.initialize():
        while True:
            totalCount += 1
            if i % 500 == 0:
                i = 0
                logger.info(f"Progress: {iterator.progress()}%")
            i += 1
            
            tree.add_element(iterator.get_native())
            # shape = iterator.get_native()
            shape = iterator.get()
            GUID = shape.data.guid
            CONTEXT = shape.data.context
            # GUID = shape.guid
            # CONTEXT = shape.context

            contexts.add(CONTEXT)

            if not shapeData.get(GUID):
                shapeData[GUID] = dict()
            
            assert(not shapeData.get(GUID).get(CONTEXT))

            shapeData[GUID][CONTEXT] = shape

            if not iterator.next():
                logger.info(f"Processed {totalCount} items")
                break

    logger.info(f"Contexts: {contexts}")

    unit_magnitude = iterator.unit_magnitude()
    unit_name = iterator.unit_name()

    return shapeData, tree, unit_magnitude, unit_name


@deprecated(
        reason="""Use processGeometry instead""",
        version="0.0.1",
)
def get_pdct_shape(element, settings):
    """Get the body shape for a single IFC element"""

    body = ifcopenshell.util.representation.get_representation(element, "Model", "Body")
    body_repr = ifcopenshell.util.representation.resolve_representation(body)
    pdct_shape = ifcopenshell.geom.create_shape(settings, inst=element, repr=body_repr)

    return pdct_shape

def get_elementShapes(elements, settings):
    """Get element shapes (body) for elements"""

    elements_shape = dict()

    for element in elements:
        pdct_shape = get_pdct_shape(element, settings)
        GUID = element.GlobalId

        elements_shape[GUID] = pdct_shape

    return elements_shape

@deprecated(
        reason="""Use processGeometry instead""",
        version="0.0.1",
)
def getCurveShapes(elements):
    """Get the axis representation for elements"""

    settings = ifcopenshell.geom.settings()
    settings.set(settings.USE_PYTHON_OPENCASCADE, True)  # tells ifcopenshell to use pythonocc

    #################
    # Extra options #
    #################

    # settings.set(settings.USE_BREP_DATA,True)
    # settings.set(settings.SEW_SHELLS,True)
    settings.set(settings.USE_WORLD_COORDS,True)
    settings.set(settings.INCLUDE_CURVES, True)
    # settings.set(settings.EDGE_ARROWS, True)

    curveShapes = list()
    for element in elements:
        axis = ifcopenshell.util.representation.get_representation(element, "Model", "Axis")
        assert axis is not None
        curve_3d_rep = ifcopenshell.util.representation.resolve_representation(axis)
        curveShape = ifcopenshell.geom.create_shape(settings, inst=element, repr=curve_3d_rep)

        curveShapes.append(curveShape)
    
    return curveShapes

def writeToFile(model, filePath):
    """Write Ifc-model to file"""

    if not filePath.endswith(".ifc"):
        filePath = filePath.join(".ifc")

    logger.info(f"Writing to {filePath}...")
    model.write(filePath)
    logger.info("Done")

def createIfcVertexPoint(point: gp_Pnt, model):
    """Create IfcVertexPoint from point"""
    P = model.create_entity("IfcCartesianPoint", **{"Coordinates": point.Coord()})
    V = model.create_entity("IfcVertexPoint", **{"VertexGeometry": P})
    return V