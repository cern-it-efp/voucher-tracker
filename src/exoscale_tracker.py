#!/usr/bin/env python3

# source: https://community.exoscale.com/api/compute/#listevents_GET

import base64
import hashlib
import hmac
import json
from urllib.request import urlopen
from urllib.parse import quote, urlencode
from cs import CloudStack
import time
import requests
import collections
import os
from aux import *
from exoscale_auth import ExoscaleAuth
from enum import Enum

Function = Enum(
    'Function', 'listUsageStatements listOrganizations listEvents suspendOrganizations listApis listChildOrganizations')

Format = Enum('Format', 'csv xlsx')

COMPUTE_ENDPOINT = "https://api.exoscale.com/compute"
suspensionThreshold = 5

exoRate_chf2eur = 1.0999
#exoRate_chf2eur = 1.099895

def chf2eur(amount):
    """Converts an amount in CHF to EUR using Exoscale's fixed rate."""

    return round(amount*exoRate_chf2eur,5)


def checkOrganizations():
    """Checks if organizations' credits are below 5. If any is, suspends it."""

    for org in exoOperation(Function.listOrganizations)["organization"]:
        if float(org["credit"]) < suspensionThreshold:
            print("Organization '%s' credit (%s) is below %s -> suspending" %
                  (org["name"], org["credit"], suspensionThreshold))
            exoOperation(Function.suspendOrganizations, orgName=org["name"])


def exoOperation(operation, rawAPI=False, orgName=None):
    """Get the Exoscale credit/consumption data. Payer organizations can query
       the list of usage-statements of their sub-organizations.
       listUsageStatements only works for delegated payment organizations."""

    if operation is None:
        operation = Function.listApis

    if rawAPI is True:
        cmd = {
            "command":           operation.name,
            "apikey":            configs["exoscale"]["apiKey"],
        }

        # Signing the request and URL encoding it
        query_string = urlencode(sign(cmd, configs["exoscale"]["apiSecret"]))

        url = f"{COMPUTE_ENDPOINT}?{query_string}"

        with urlopen(url) as f:
            return json.load(f)
    else:
        cstack = CloudStack(endpoint='https://api.exoscale.com/compute',
                            key=configs["exoscale"]["apiKey"],
                            secret=configs["exoscale"]["apiSecret"])

        if operation is Function.listUsageStatements:
            return cstack.listUsageStatements()
        elif operation is Function.listEvents:
            return cstack.listEvents()
        elif operation is Function.listOrganizations:
            return cstack.listOrganizations()
        elif operation is Function.suspendOrganizations:
            return cstack.suspendOrganizations(name=orgName)
        elif operation is Function.listChildOrganizations:
            res = []
            for org in cstack.listOrganizations()["organization"]:
                if org["name"] != "cern-distributor-playground":
                    res.append(org)
            return res
        else:
            return cstack.listApis()


def exoInternalAPI(useExoAuth=True):
    """Uses https://portal.exoscale.com/api/usage/ignacio.peluaga.lozada@cern.ch
       Requires a browser session (cookie) and provides billing details for the
       current month only."""

    url = "https://portal.exoscale.com/api/usage/%s" % configs["exoscale"]["account"]
    if useExoAuth is False:
        cookies = {"session": configs["exoscale"]["session"]}
        return requests.get(url, cookies=cookies).text
    else:
        auth = ExoscaleAuth(
            configs["exoscale"]["apiKey"], configs["exoscale"]["apiSecret"])
        return requests.get(url, auth=auth).text


def getPriceList(format=None, json=True):
    """Downloads the price list using the internal API.
       By default gets the csv format."""

    url = "https://portal.exoscale.com/api/reporting/download/168/%s"
    if format is Format.xlsx:
        url = url % "xlsx"
    else:
        url = url % "csv"

    cookies = {"session": configs["exoscale"]["session"]}
    auth = ExoscaleAuth(configs["exoscale"]["apiKey"],
                        configs["exoscale"]["apiSecret"])

    headers = {'x-csrf-token': 'rHWx1234abcd',
               'x-exo-token': 'rHWx1234abcd',
               'referer': 'https://portal.exoscale.com/u/cern-distributor-playground/distributor/reporting'}

    # TODO: VALID RESPONSES ONLY 200??
    return requests.post(url, auth=auth).text if json is False else csv2json(requests.post(url, auth=auth).text)
    # return requests.post(url, cookies=cookies, headers=headers).text


def last24HoursUsage(org, format=None, json=True):
    """Given an organization, gets the last 24h usage details report.
       By default gets the csv format."""

    url = "https://portal.exoscale.com/api/reporting/download/167/%s"

    if format is Format.xlsx:
        url = url % "xlsx"
    else:
        url = url % "csv"

    data = {"args": [{"id": "2c051824-2cbb-7470-d558-41d48c595efb", "name": "scope", "display-name": "Scope", "type": "text", "required": True, "display_name": "Scope"},
                     {"id": "3d837851-9951-60dd-e63d-262e411915bf", "name": "exoid", "display-name": "ExoID", "type": "text", "required": True, "display_name": "ExoID", "value": str(org)}]}

    auth = ExoscaleAuth(configs["exoscale"]["apiKey"],
                        configs["exoscale"]["apiSecret"])

    headers = {'x-csrf-token': 'rHWx1234abcd',
               'x-exo-token': 'rHWx1234abcd',
               'referer': 'https://portal.exoscale.com/u/cern-distributor-playground/distributor/reporting'}

    #return requests.post(url, cookies=cookies, json=data, headers=headers).text
    if json is False:
        return requests.post(url, auth=auth, json=data).text
    else:
        return csv2json(requests.post(url, auth=auth, json=data).text)


def getMonetary(pl, variable, qty): # TODO: this might not be the best solution performance wise
    """Goes through the list of prices and calculates the amount spent on
       service specified by variable, using qty as quantity."""
    res = 0
    for price in pl:
        if price["name"] in variable:
            res = float(price["price"])*qty
    return res


def getLast24hsMonetary(org):
    """Combines getPriceList and last24HoursUsage to get the monetary value
       of last 24 hours consumption grouped by services."""

    pl = getPriceList()
    usage = last24HoursUsage(org["name"])
    res = {}

    if len(pl) is 0 and len(usage) is 0: # TODO: these are empty when using distributor's IAM API keys
        return res

    consumedLast24hs = 0
    services = set()

    res["organization"] = org["name"] # ["roles"][0]["email"]
    res["people"] = org["roles"] # [0]["email"]
    res["currency"] = pl[0]["currency"]
    res["code"] = org["client_id"]
    res["remaining"] = float(org["credit"])

    for entry in usage:
        consumedLast24hs += getMonetary(pl, entry["variable"], float(entry["qty"]))
        services.add(entry["variable"])

    if consumedLast24hs > 0:
        res["lastUsage"] = "%sT00:00:00Z" % time.strftime("%Y-%m-%d")
    else:
        res["lastUsage"] = None

    res["consumedLast24hs"] = consumedLast24hs
    res["services"] = list(services)

    return res


def getVouchers():
    res = []
    for org in exoOperation(Function.listChildOrganizations):
        res.append(getLast24hsMonetary(org))
    return res

# PERSONAL () | HNSCICLOUD (SUSPENDED) | DISTRIBUTOR (DISTRIBUTOR)

# print(json.dumps(exoOperation(Function.listEvents,rawAPI=True))) #  OK | 401 Unauthorized | OK
# print(json.dumps(exoOperation(Function.listOrganizations,rawAPI=True))) #  403 forbidden | 403 forbidden | HTTP Error 500: Internal Server Error
# print(json.dumps(exoOperation(Function.listUsageStatements,rawAPI=True))) #  403 forbidden | 403 forbidden | HTTP Error 500: Internal Server Error

# print(json.dumps(exoOperation(Function.listEvents))) #  OK | HTTP 401 response from CloudStack | OK
# print(json.dumps(exoOperation(Function.listOrganizations))) #  403 forbidden | HTTP 403 response from CloudStack | OK
# print(json.dumps(exoOperation(Function.listUsageStatements))) #  403 forbidden | HTTP 403 response from CloudStack | OK

# checkOrganizations()

# print(json.dumps(exoOperation(operation=None)))
# print(json.dumps(exoOperation(operation=None,rawAPI=True)))
# print(json.dumps(exoOperation(operation=Function.listApis,rawAPI=True)))
# print(json.dumps(exoOperation(operation=Function.suspendOrganizations)))

# print(exoInternalAPI()) # OK w. consumption | 401 error: Invalid authorization header | OK w/o consumption

#print(json.dumps(last24HoursUsage("cern-distributor-test-client")))
#print(last24HoursUsage("cern-distributor-test-client", json=False))

#print(json.dumps(getPriceList())) # TODO: distributor's IAM keys are not authorized to download the report but this call does not report it! but instead returns an empty array
#print(getPriceList(json=False))

#print(json.dumps(getLast24hsMonetary("cern-distributor-test-client")))

#print(json.dumps(exoOperation(Function.listChildOrganizations))) #  403 forbidden | HTTP 403 response from CloudStack | OK

print(json.dumps(getVouchers()))
#print(getVouchers())
#getVouchers()
