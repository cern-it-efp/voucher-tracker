#!/usr/bin/env python3

import exoscale_tracker
from enum import Enum
import aws_tracker
import sys
sys.path.append('src/azure')
import az_cli_python as azure_tracker
import time
import json
import csv
import voucherify
import google_tracker
from aux import *
import getopt
#import cloudsigma_tracker

# TODO: resellers of any other provider possible?
Provider = Enum('Provider', 'AWS Azure Google Micromail TISparkle')

def loadVouchers(csvPath=None):
    """If a path is given, loads the csv file from the path, returns it
       as dict object. Otherwise gets the vouchers from voucherify.io."""
    if csvPath is None:
        return voucherify.getAllVouchers()
    else:
        with open(csvPath, newline='') as csvfile:
            res = []
            for row in csv.DictReader(csvfile):
                res.append(row)
            return res


def initChecks():
    """Check that configs.yaml exists and is valid and also check that vouchers
       exist on voucherify. In case of errors returns False."""
    return True


# TODO: convention? uppercase, lowercase, amazon or aws, gcp or google, special characters...
def checkProvider(rightProviders, providerToCheck):
    """Returns whether the providers received match."""

    for p in rightProviders:
        if providerToCheck.lower() == p.name.lower():
            return True
    return False


def makeFlat(nestedOrList):
    """Takes the received object and returns a flatten object, i.e string that
       can be feed to voucherify's metadata."""

    if isinstance(nestedOrList, list):
        nestedOrList.sort()
        return ' / '.join(nestedOrList)
    else:
        print("turn the dict into a string") # TODO


def checkResponse(voucherifyResponse):
    """Check Voucherify's response"""

    if isinstance(voucherifyResponse, list):
        print(voucherifyResponse[0])
    else:
        print("ERROR: %s" % voucherifyResponse)


def banner(msg):
    """Print provider header"""

    fill = configs["general"]["msgSize"] - len(msg)
    print("\n##############################")
    print("#    Updating %s's%s   #" % (msg,fill*" "))
    print("##############################")


def updateAzure():
    """Retrieves billing data from Azure and updates it on Voucherify."""
    # TODO: exceptions "too many 500 responses" have been seen frequently
    banner("Azure")
    for voucher in azure_tracker.getVouchers():
        for assignedVoucher in allAsignedVouchers:
            # TODO: edited the csv and changed emails by tenantIds as w/a
            if voucher["tenantId"] == assignedVoucher["Email"] and checkProvider([Provider.Azure, Provider.Micromail], assignedVoucher["Provider"]):
                # redeem = True if voucher["spent"] != 0 else None # TODO: if it is listed it is bc the user gave me access to the subscription as billing reader and the subscription is created when redeming the voucher
                redeem = True if assignedVoucher["Redeemed"] is 0 else False

                voucherifyResponse = voucherify.updateVoucher(
                    assignedVoucher["Code"],
                    amount=abs(voucher["spent"]),
                    services=makeFlat(voucher["services"]),
                    last_usage=voucher["lastUsage"],
                    redeem=redeem)

                checkResponse(voucherifyResponse)


def updateAWS():
    """Retrieves billing data from AWS and updates it on Voucherify."""
    banner("AWS")
    for voucher in aws_tracker.getVouchers():
        for assignedVoucher in allAsignedVouchers:
            if voucher["Email"] == assignedVoucher["Email"] and checkProvider([Provider.AWS, Provider.TISparkle], assignedVoucher["Provider"]):
                # TODO: if it is listed, it means it was redeemed, right? what about on the other providers? if it is listed, shouldn't it be always reddemed = True? like azure
                redeem = True if voucher["spent"] != 0 and assignedVoucher["Redeemed"] is 0 else False

                voucherifyResponse = voucherify.updateVoucher(
                    assignedVoucher["Code"],
                    amount=abs(voucher["spent"]),
                    services=makeFlat(voucher["services"]),
                    last_usage=voucher["lastUsage"],
                    redeem=redeem)

                checkResponse(voucherifyResponse)


def updateGoogle():
    """Retrieves billing data from GCP and updates it on Voucherify."""

    banner("GCP")
    for voucher in google_tracker.getVouchers():
        assignedVoucher = next(
            filter(lambda x: x['Code'] == voucher["code"], allAsignedVouchers))
        redeem = True if voucher["spent"] != 0 and assignedVoucher["Redeemed"] is 0 else False

        voucherifyResponse = voucherify.updateVoucher(
            voucher["code"],
            amount=abs(voucher["spent"]),
            services=makeFlat(voucher["services"]),
            last_usage=voucher["lastUsage"],
            redeem=redeem)

        checkResponse(voucherifyResponse)


def updateExoscale():
    """Retrieves billing data from Exoscale and updates it on Voucherify."""

    banner("Exoscale")
    for voucher in exoscale_tracker.getVouchers():

        assignedVoucher = next(
            filter(lambda x: x['Code'] == voucher["code"], allAsignedVouchers))
        # TODO: how to deal here with different currencies?
        initialAmount = assignedVoucher["Value"]

        redeem = False
        # TODO: how is this managed on the other providers?
        last_usage = assignedVoucher["lastUsage"] if voucher["lastUsage"] is None else voucher["lastUsage"]

        if assignedVoucher["Redeemed"] is 1:
            # TODO: for someone that did not redeem the voucher yet voucher["remaining"] is 0.00
            spent = initialAmount - voucher["remaining"]
        elif assignedVoucher["Redeemed"] is 0 and voucher["remaining"] == 0:
            spent = 0  # "NOT_REDEEMED_YET"
            last_usage = "NOT_REDEEMED_YET"
        elif assignedVoucher["Redeemed"] is 0 and voucher["remaining"] > 0:
            spent = initialAmount - voucher["remaining"]
            redeem = True

        voucherifyResponse = voucherify.updateVoucher(
            voucher["code"],
            amount=abs(spent),
            services=makeFlat(voucher["services"]),
            last_usage=last_usage,
            redeem=redeem)

        checkResponse(voucherifyResponse)


def updateCloudSigma():
    """Retrieves billing data from CloudSigma and updates it on Voucherify."""
    banner("CloudSigma")
    print("(to be done)")


def updateTSystems():
    """Retrieves billing data from T-Systems and updates it on Voucherify."""
    banner("T-Systems")
    print("(to be done)")


def updateCloudferro():
    """Retrieves billing data from Cloudferro and updates it on Voucherify."""
    banner("Cloudferro")
    print("(to be done)")


def main():
    """Runs once per day"""

    while True:
        global allAsignedVouchers
        allAsignedVouchers = loadVouchers()
        if len(allAsignedVouchers) is 0:
            print("\nNo vouchers were found to update.")
            sys.exit()
        if initChecks() is not True:
            print("%s - Initial checks failed. Trying again in 20 minutes..." %
                  time.strftime("%Y-%m-%d / %H:%M:%S"))
            time.sleep(1200)
        else:  # TODO: in case any update fails, smth has to be loged or noticed, otherwise the voucherify dashboard will not be updated
            # -----------
            # Americans
            # -----------
            updateGoogle()
            updateAzure()
            updateAWS()

            # -----------
            # Europeans
            # -----------
            updateExoscale()
            # updateCloudSigma()
            # updateTSystems()
            # updateCloudferro()

            print("\n--------------------------------------------------")
            print("| %s - new update in 24 hours |" %
                  time.strftime("%Y-%m-%d / %H:%M:%S"))
            print("--------------------------------------------------")
            time.sleep(configs["general"]["sleepTime"])  # 86400


# -----------------CMD OPTIONS--------------------------------------------
try:
    options, values = getopt.getopt(sys.argv[1:], "i:", ["import="])
except getopt.GetoptError as err:
    print(err)
    sys.exit(1)
for currentOption, currentValue in options:
    if currentOption in ['-i','--import']:
        voucherify.importVouchers(currentValue)
        sys.exit(0)
# -----------------------------------------------------------------------


main()
