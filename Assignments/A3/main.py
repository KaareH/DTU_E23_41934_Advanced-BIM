"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import sys
import ifcopenshell
import ifcopenshell.util.classification
import ifcopenshell.util.schema
from loguru import logger

from pyconbim.geomUtils import *
from pyconbim.ifcUtils import *
from pyconbim.rendering import *
from pyconbim.analyticalModel import *
import pyconbim.utils

import createIfcAnalyticalModel
import doPyNiteFEA

def runThis():
    models = load_models(model_dir='./models',
                     models={'simple-frame': 'simple-frame.ifc',
                             'simple-frame-with-slab': 'simple-frame-with-slab.ifc',
                             'simple-frame-with-slab-holes': 'simple-frame-with-slab-holes.ifc',
                             'simple-frame-with-slab-wall': 'simple-frame-with-slab-wall.ifc',
                             })
    # model = models['simple-frame']
    model = models['simple-frame-with-slab-wall']
    
    # models = load_models(model_dir="./models",
    #                      models={
    #                          'building': 'AC20-Institute-Var-2.ifc',
    #                      })
    # model = models['building']

    # models = load_models(model_dir='./models',
    #                      models={'stru': 'LLYN - STRU.ifc',
    #                             #  'ark': 'LLYN - ARK.ifc',
    #                          })
    # model = models['stru']
    
    aModel = createIfcAnalyticalModel.runThis(model, outputFileName="analyticalModel.ifc")
    doPyNiteFEA.runThis(aModel)

if __name__ == "__main__":
    logger.info(f"ifcopenshell version: {ifcopenshell.version}")
    logger.info(f"Python-version {sys.version}")

    this_file = os.path.realpath(__file__)
    try:
        logger.info(f"Changing directory to {os.path.dirname(this_file)}")
        os.chdir(os.path.dirname(this_file))
    except Exception as e:
        logger.exception(f"Failed to change directory to {os.path.dirname(this_file)}")
        logger.exception(e)
        exit(1)

    runThis()

    logger.info("Done.")
    exit(0)
