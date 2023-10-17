"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import os
import sys

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
