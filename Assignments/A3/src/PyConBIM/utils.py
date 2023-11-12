"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23

Misc. utils
"""

def sampleUtil():
    """Function for testing"""
    return "abc1234567"

def getElementsRender(guids, model):
    elements_render = list()
    for guid in guids:
        element = model.by_guid(guid)
        elements_render.append(element)

    print(f"Length of list: {len(elements_render)}")
    return elements_render
