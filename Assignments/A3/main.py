"""
Kaare G. S. Hansen, s214282 - DTU
41934 - Advanced BIM, E23
"""

import sys
import os
import click
import json
import ifcopenshell
import ifcopenshell.util.classification
import ifcopenshell.util.schema
from loguru import logger

import pyconbim.ifcUtils as ifcUtils

import createIfcAnalyticalModel
import doPyNiteFEA

@click.group()
def cli():
    pass

@cli.command()
@click.argument('modeloption', nargs=1)
def run(modeloption):
    click.echo(f"Running {modeloption}")
    # modeloption = modeloption.lower()

    # Opening JSON file
    f = open ('./input/config.json', "r")
    config = json.loads(f.read())

    # Check if model option is valid
    modelOptions = [modelConf['name'] for modelConf in config['model-configurations']]
    if modeloption not in modelOptions:
        logger.error(f"Unknown model option {modeloption}")
        logger.info(f"Available options: {modelOptions}")
        exit(1)

    # Get model configuration
    index = modelOptions.index(modeloption)
    modelConf = config['model-configurations'][index]

    # Load model
    models = ifcUtils.load_models(model_dir=config['general_config']['model_directory'],
                                  models={modelConf['name']: modelConf['filename']})
    model = models[modelConf['name']]

    # Find preprocess file
    preprocess_file = os.path.join('input', modelConf['preprocess_file'])
    
    logger.disable("pyconbim.geomUtils") # Temporary, until issue is fixed
    
    outputFilePath = os.path.join(config['general_config']['output_directory'], modelConf['analytical_output_filename'])

    # Create model
    aModel = createIfcAnalyticalModel.runThis(model, outputFilePath=outputFilePath, preprocess_file=preprocess_file)

    if config['general_config']['run_pynite']:
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

    cli()

    logger.info("Done.")
    exit(0)
