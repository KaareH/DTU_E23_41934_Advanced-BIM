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
                             'simple-frame-with-slab': 'simple-frame-with-slab.ifc',
                             })
    # model = models['simple-frame']
    model = models['simple-frame-with-slab']
    
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
    print(f"ifcopenshell version: {ifcopenshell.version}")
    print(f"Python-version {sys.version}")

    this_file = os.path.realpath(__file__)
    try:
        print(f"Changing directory to {os.path.dirname(this_file)}")
        os.chdir(os.path.dirname(this_file))
    except Exception as e:
        print(f"Failed to change directory to {os.path.dirname(this_file)}")
        print(e)
        exit(1)

    runThis()

    print("Done.")
    exit(0)
