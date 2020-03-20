#!/usr/bin/env python3

import yaml

with open("../../configs.yaml", 'r') as inputfile:
    try:
        configs = yaml.load(inputfile, Loader=yaml.FullLoader)
    except AttributeError:
        try:
            configs = yaml.load(inputfile)
        except yaml.scanner.ScannerError:
            print("Error loading yaml file " + loadThis)
            stop(1)
    except yaml.scanner.ScannerError:
        print("Error loading yaml file " + loadThis)
        stop(1)
