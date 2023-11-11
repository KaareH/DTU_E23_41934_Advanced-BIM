# Assignment 3 - OpenBIM Change

[![Build Status](https://github.com/KaareH/DTU_E23_41934_Advanced-BIM/actions/workflows/python-package-conda-A3.yml/badge.svg)](https://github.com/KaareH/DTU_E23_41934_Advanced-BIM/actions)

__41934 - Advanced BIM, E23__ - _Technical University of Denmark_

**Group 48:**
- Kaare G. S. Hansen, s214282 - DTU

## Noter til aflevering

- Concept of novice to guru
- Hvad kan jeg bidrage med?
- Diagrammer
    - Lav abstrakt overordnet diagram (Indholder create analytical model, henviser til andet diagram)
    - Lav diagram med implementering af create analytical model. (Farv de dele jeg rent faktisk har implmenteret)


## Future development ideas

If I had the time and resources to develop the tool further:

- Analyse steel-connections and create new geometry for the optimal connection
- Resize profile dimensions according to requirements
- Parametric library of structural connections
- Generate report of requirements... E.g. highlight members that exceed deflection requiremnets...

## Reflection
- ifcopenshell provided axis are not reliable. May be entirely out of actual elements OBB.


## IDM diagrams

### Abstract specified IDM

The IDM diagram for the final intended (but unimplemented) tool:

<!--
https://demo.bpmn.io/new
-->
![IDM-abstract](diagrams/IDM-abstract.svg)


### Implemented IDM

The IDM diagram that describes the tool implemented in this assignment.

Colored in red is implemented parts:

![IDM-implemented](diagrams/IDM-implemented.svg)


## Using the tool

### Prerequisites for script-execution

In addition to common Python-modules, Open Cascade is required.

Refer to below files for specified environment:

- [`environment.yml`](environment.yml)
- [`requirements.txt`](requirements.txt)
