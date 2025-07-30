# Convert Custom URI to Autonumber

## Introduction

This Python script allows you to process linked data set that uses any kind of self-defined URIs for subjects to use auto-numbered URIs. In some cases this results in improved maintainability as well as more flexibility when adding or restructuring data. The script is configurable to look for a certain term and replaces the custom URI with an automatically generated incremental number within a defined range. 

## How to use

1. python -m venv .venv
2. pip install -r requirements.txt
3. configure your range, input file, output file format, output file, and base URI in the script
4. run with python convert-skos-concept-to-autonumber.py

## Configuration

The INPUT_FILE defines the filepath pointing to the linked data set to be processed. Currently, only TTL seems to be working. 
OUTPUT_FORMAT defines the output format.
OUTPUT_FILE defines the filepath to write the output file to.
BASE_URI defines the base URI of the term to be changed.
TARGET_TERM defines the term to be replaced. 
NEW_DF is optional and defines the new format for DCTERMS:created and DCTERMS:modified, if not needed remove variable initialization.
