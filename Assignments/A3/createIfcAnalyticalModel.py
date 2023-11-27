# Kaare G. S. Hansen, s214282 - DTU
# 41934 - Advanced BIM, E23

"""
Create an IfcStructuralAnalysisModel from an IFC file and write to disk.

"""

import sys
import json
from loguru import logger
import ifcopenshell

from pyconbim.geomUtils import *
from pyconbim.ifcUtils import *
from pyconbim.rendering import *
from pyconbim.analyticalModel import *
import pyconbim.utils
import pyconbim.modelPreprocessor as modelPP

from PyNite import FEModel3D
from PyNite.Visualization import Renderer

def runThis(model, outputFilePath, preprocess_file):
    modelData = ModelData(model)
    modelPP.preProcessModel(modelData, preprocess_file)

    elements = modelData.get_structuralMembers()
    aModel = AnalyticalModel()
    aModel.add_elements(elements, modelData)
    aModel.solve_connections()
    aModel.merge_nodes()

    # nodes = aModel.get_nodes()
    # for key, node in nodes.items():
    #     print(key, node.get_point().Coord())
    #     rendering.addDebugShape(node.get_point())

    # RenderInWindow(debugRenderFunc)
    RenderInWindow(RenderStructuralMembersFunc, modelData=modelData, analyticalModel=aModel)

    logger.info(f"Creating IfcStructuralAnalysisModel...")
    aModel.to_ifc_analysisModel(modelData.model)

    pyconbim.ifcUtils.writeToFile(modelData.model, outputFilePath)

    return aModel
