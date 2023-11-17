"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import sys
import ifcopenshell

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
                             })
    model = models['simple-frame']
    
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
    
    aModel = createIfcAnalyticalModel.runThis(model, outputFileName="./output/analyticalModel.ifc")
    doPyNiteFEA.runThis(aModel)

if __name__ == "__main__":
    print(f"ifcopenshell version: {ifcopenshell.version}")
    print(f"Python-version {sys.version}")

    runThis()

    print("Done.")
    exit(0)
