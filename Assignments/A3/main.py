"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import sys
import ifcopenshell

from pyconbim.geomUtils import *
from pyconbim.ifcUtils import *
from pyconbim.rendering import *
import pyconbim.utils

def runThis():
    models = load_models(model_dir='/Users/Kaare/My Drive/DTU/Kurser/Videregaaende BIM - 41934/IFC-models\SkyLab',
                     models={'ark': 'LLYN - ARK.ifc',
                             'stru': 'LLYN - STRU.ifc',
                             })


    model = models['stru']
    modelData = ModelData(model)

    print(len(modelData.shapes))

    shapes = [shape['Body'].geometry for _, shape in modelData.shapes.items()]

    print("Ready to render in window")
    RenderInWindow(SimpleRenderFunc, shapes=shapes)


if __name__ == "__main__":
    print(f"ifcopenshell version: {ifcopenshell.version}")
    print(f"Python-version {sys.version}")
    # print("See AdvBIM-A2_Analysis.ipynb")

    runThis()
