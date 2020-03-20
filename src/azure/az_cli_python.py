#!/usr/bin/env python3

import json
import os
from azure.cli.core import get_default_cli  # requires 'pip3 install azure-cli'
from aux import *
import sys
from datetime import datetime, timedelta
import subprocess

allBP_startDate="2019-01-01"
allBP_endDate="2023-01-01"

def az_cli(args_str):
    args = args_str.split()
    cli = get_default_cli()
    cli.invoke(args, out_file=open(os.devnull, 'w')) # method of knack pachage (pip3 show knack)
    #cli.invoke(args, out_file=open(os.devnull, 'w'), stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
    #subprocess.call(cmd, shell=True, stdout=open(os.devnull, 'w'), stderr=subprocess.STDOUT)
    if cli.result.result:
        return cli.result.result
    elif cli.result.error:
        raise cli.result.error
    return True


def consumptionUsageList(subscription_id=None, getAllBP=False, startDate=None, endDate=None):
    """Pythonized version of az CLI as SDK lacks AIOs support.
       By default returns the billing data from the current billing period for
       the deault subscription."""

    res = []
    azCMD = "consumption usage list -am" # options 'a' to include additional properties and 'm' to include meter details

    if subscription_id is not None:
        azCMD += " --subscription %s" % subscription_id

    # TODO: wrap the following stuff in a try/catch

    if startDate is not None and endDate is not None: # TODO: the default range fails for AIOs subs, but a range 18-19 works
        azCMD += " --start-date %s --end-date %s" % (startDate, endDate)
    elif getAllBP is True: # TODO: this will fail if the subscription has only the current billing period (ie. running this for the IPLazureInOpen sub. in november
        azCMD += " --start-date %s --end-date %s" % (allBP_startDate, allBP_endDate)

    #print("Will run: %s" % azCMD)

    returnedFromCLI = az_cli(azCMD)

    if isinstance(returnedFromCLI, list) and len(returnedFromCLI) > 0:
        for obj in returnedFromCLI:
            if float(obj["pretaxCost"]) > 0:
                res.append(obj)
    # ------------------------------------------------------------------------------------
    return res


def getSubscriptions(name=None, subscription_id=None):
    """Returns a list of all the subscriptions the currently loged in account
       has access to."""
    accList = az_cli("account list --refresh")
    if name is not None:
        for acc in accList:
            if acc["name"] == name:
                return acc
    elif subscription_id is not None:
        for acc in accList:
            if acc["subscription_id"] == subscription_id:
                return acc
    else:
        return accList


# TODO: another aproach would be to do this directly against the API: create the voucher when requesting at the subscription level (ie for each subscription download all the stuff and create a voucher object)
def getVouchers(allBillingData=None):
    """Goes through the whole billing data object and groups it by subscriptions"""

    az_cli("login --service-principal -u %s -p %s -t %s" % (configs["azure"]["user"],configs["azure"]["pass"],configs["azure"]["tenant"]))

    #az_cli("login -u %s -p %s" % (configs["azure"]["user"],configs["azure"]["pass"]))

    res = []
    allSubscriptions = getSubscriptions()

    if allSubscriptions is True:
        return res

    if allBillingData is None:
        allBillingData = []
        for subscription in allSubscriptions:
            if "Azure in Open" in subscription["name"]:
                allBillingData += consumptionUsageList(subscription_id=subscription["id"],getAllBP=True)

    for subscription in allSubscriptions:

        groupedCons = {}
        groupedCons["subscriptionID"] = subscription["id"]
        groupedCons["subscriptionName"] = subscription["name"]
        groupedCons["tenantId"] = subscription["tenantId"]
        groupedCons["lastUsage"] = ""
        groupedCons["spent"] = 0
        services = set()
        locations = set()

        for obj in allBillingData:
            if subscription["name"] == obj["subscriptionName"]:
                services.add("%s - %s" % (obj["meterDetails"]["meterCategory"], obj["meterDetails"]["meterName"]))
                locations.add(obj["instanceLocation"])
                groupedCons["lastUsage"] = obj["usageEnd"] if obj["usageEnd"] > groupedCons["lastUsage"] else groupedCons["lastUsage"]
                groupedCons["spent"] += float(obj["pretaxCost"])

        groupedCons["services"] = list(services)
        groupedCons["locations"] = list(locations)

        res.append(groupedCons)
    return res


print(json.dumps(getVouchers()))
