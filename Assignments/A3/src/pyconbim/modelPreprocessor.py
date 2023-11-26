# Kaare G. S. Hansen, s214282 - DTU
# 41934 - Advanced BIM, E23

""" Ifc model preprocessor.

Preprocess an IFC-model before analysis.
Preprocessing reads a JSON-file with corrections and applies them to the model.

Corections include:
    - Marking elements as load-bearing.
        * Some elements might be falsely marked.
    - Ignoring elements.
        * Elements that are not relevant or disturbs the analysis.
    - Enlarging the OBB of elements.
        * Elements that are not correctly modelled, and hence cannot connect naturally.

"""

import json
from loguru import logger
import ifcopenshell

def alter_loadBearing(mark_loadBearing, modelData):
    model = modelData.model
    for alter in mark_loadBearing:
        GUID = alter['GUID']
        loadBearing = alter['loadBearing']

        element = model.by_guid(GUID)
        ifc_pset_common = 'Pset_' +  (str(element.is_a()).replace('Ifc','')) + 'Common'

        pset_common = ifcopenshell.api.run("pset.add_pset", model, product=element, name=ifc_pset_common)
        logger.debug(pset_common)

        ifcopenshell.api.run(
            "pset.edit_pset",
            model,
            pset=pset_common,
            properties={"LoadBearing": loadBearing},
        )
    logger.info(f"Marked {len(mark_loadBearing)} elements as load-bearing.")
    
def ignoreElement(ignore_element, modelData):
    GUIDS_ignore = set()
    for ignore in ignore_element:
        GUID = ignore['GUID']
        if ignore['ignore']:
            GUIDS_ignore.add(GUID)

    modelData.GUIDS_ignore = GUIDS_ignore
    logger.info(f"Ignored {len(GUIDS_ignore)} elements.")

def enlarge_OBB(enlarge_OBB, modelData):
    model = modelData.model
    GUIDS_enlarge = dict()
    for enlarge in enlarge_OBB['by_type']:
        TYPE_GUID = enlarge['GUID']
        elementType = model.by_guid(TYPE_GUID)
        elements = ifcopenshell.util.element.get_types(elementType)
        for element in elements:
            GUIDS_enlarge[element.GlobalId] = enlarge['enlarge']
    
    modelData.GUIDS_enlarge = GUIDS_enlarge
    logger.info(f"{len(GUIDS_enlarge)} elements marked for additional OBB enlargement.")

def mark_foundation(mark_foundation, modelData):
    model = modelData.model
    GUIDS_foundation = set()
    for mark in mark_foundation['by_type']:
        TYPE_GUID = mark['GUID']
        elementType = model.by_guid(TYPE_GUID)
        elements = ifcopenshell.util.element.get_types(elementType)
        # Only marks as foundation if true. Doesn't unmark.
        if mark['foundation']:
            for element in elements:
                GUIDS_foundation.add(element.GlobalId)

    # TODO: Implement by_keyword
    # for mark in mark_foundation['by_keyword']:
        # pass

    modelData.GUIDS_foundation = GUIDS_foundation
    logger.info(f"Marked {len(GUIDS_foundation)} elements as foundation.")

def preProcessModel(modelData, filepath):
    logger.info("Preprocessing model...")
 
    # Opening JSON file
    f = open (filepath, "r")
    data = json.loads(f.read())

    correctionFunctions = {
        "alter_loadBearing": alter_loadBearing,
        "ignoreElement": ignoreElement,
        "enlarge_OBB": enlarge_OBB,
        "mark_foundation": mark_foundation,
    }

    corrections = data['corrections']
    for key, correction in corrections.items():
        if key in correctionFunctions:
            correctionFunctions[key](correction, modelData)
        else:
            logger.warning(f"Unknown correction: {key}")

    # Float beams på tag
    # TypeName: Rectangular and Square Hollow Sections:SB10
    # Type GUID 16iVztvQvBdxi_mREc593p
    # Type GUID 3cgthokUX8HuAcV5wVTtxB
    # Udvid deres OBB

    # SlabType BrøndFundament
    # SlabType floor, Name=DK5
    # Slab Typeenum Baseslab er foundation
    # Søg på foundation, fundament i Pset_ReinforcementBarPitchOfWall
    # BrøndFundament er ikke markeret loadBearing

    logger.info("Preprocessing model finished.")
