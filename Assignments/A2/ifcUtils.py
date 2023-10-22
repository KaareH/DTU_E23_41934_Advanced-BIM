"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import os
import sys
import multiprocessing

import ifcopenshell
import ifcopenshell.util.placement
import ifcopenshell.geom
import ifcopenshell.util.shape
import ifcopenshell.util.selector

model_dir = "/Users/Kaare/My Drive/DTU/Kurser/Videregaaende BIM - 41934/IFC-models"

model_file_ark = "SkyLab/LLYN - ARK.ifc"
model_file_stru = "SkyLab/LLYN - STRU.ifc"

def load_models():
    model_paths = dict()
    model_paths['ark'] = os.path.join(model_dir, model_file_ark)
    model_paths['stru'] = os.path.join(model_dir, model_file_stru)

    models = dict()
    for key, model_path in model_paths.items():
        print(f"File path, {key}: {model_path}")
        model = ifcopenshell.open(model_path)
        print(f"Model schema: {model.schema}\n")
        models[key] = model
    
    return models

def getLoadBearing(model):
    load_bearing = list(ifcopenshell.util.selector.filter_elements(model,
    "IfcBuildingElement, /Pset_.*Common/.LoadBearing=TRUE"))

    unique_types = set(el.get_info()['type'] for el in load_bearing)

    print(f"Number of load-bearing elements: {len(load_bearing)}")
    print(f"Unique types of loadbearing elements:\n {unique_types}")

    return load_bearing

def processGeometry(model):
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

    print(f"Beginning processing with {CORE_COUNT} threads...")
    contexts = set()
    shapeData = dict()

    totalCount = 0
    i = 0
    if iterator.initialize():
        while True:
            totalCount += 1
            if i % 500 == 0:
                i = 0
                print(f"Progress: {i} {iterator.progress()}%")
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
                print(f"Processed {totalCount} items")
                break

    print(f"Contexts: {contexts}")

    unit_magnitude = iterator.unit_magnitude()
    unit_name = iterator.unit_name()

    return shapeData, tree, unit_magnitude, unit_name

