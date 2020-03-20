#!/usr/bin/env python3

import csv
import sys
import yaml
import json
import base64
import hashlib
import hmac
from urllib.request import urlopen
from urllib.parse import quote, urlencode
import time
import requests
import collections
import os
from enum import Enum

Currency = Enum('Currency', 'CHF € £ $')

with open("configs.yaml", 'r') as inputfile:
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


def sign(command, secret):
    """Adds the signature bit to a command expressed as a dict"""
    # order matters
    arguments = sorted(command.items())

    query_string = "&".join("=".join((key, quote(value, safe="*")))
                            for key, value in arguments)

    # Signing using HMAC-SHA1
    digest = hmac.new(
        secret.encode("utf-8"),
        msg=query_string.lower().encode("utf-8"),
        digestmod=hashlib.sha1).digest()

    signature = base64.b64encode(digest).decode("utf-8")

    return dict(command, signature=signature)


def csv2json(csvContent):
    """Converts csv content to json."""
    res = []
    {res.append(row) for row in csv.DictReader(csvContent.splitlines())}
    return res


def convertCurrency(amount, fromCurrency, toCurrency):
    """Given an amount in a currency 'from' return its value in
       currency 'to'."""
    print("todo")
