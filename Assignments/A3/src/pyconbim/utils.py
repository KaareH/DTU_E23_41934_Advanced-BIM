"""
Misc. utilities

Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import numpy as np

def sampleUtil():
    """Function for testing"""
    return "abc123456789"

def getElementsRender(guids, model):
    elements_render = list()
    for guid in guids:
        element = model.by_guid(guid)
        elements_render.append(element)

    print(f"Length of list: {len(elements_render)}")
    return elements_render

def getAffineTransformation(transformation) -> np.ndarray:
    """Get affine transformation numpy-matrix from gp_Trsf"""

    transformation = transformation.Inverted()
    matrix = np.zeros((3,4))
    for i, row in enumerate(matrix):
        for j, _ in enumerate(row):
            # Very weird, indices starts at 1 for gp_Trsf.Value()
            matrix[i, j] = transformation.Value(i + 1, j + 1)
    matrix = np.append(matrix, [[0, 0, 0, 1]], axis=0)
    
    return matrix