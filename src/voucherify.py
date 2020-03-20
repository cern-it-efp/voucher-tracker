#!/usr/bin/env python3

import requests
import json
import yaml
import time
from aux import *

baseAPI = "https://api.voucherify.io/v1"


headers = {'X-App-Id': configs['voucherify']['appId'],
           'X-App-Token': configs['voucherify']['appToken'],
           'Content-Type': 'application/json'}

# TODO - for RESTful best practices keep in mind not allowed: POST over a single resource & PUT over a collection

def importVouchers(path):
    """Import the vouchers on the CSV located on the specified path.
       The CSV file has to include headers in the first line.
       All properties which cannot be mapped to standard voucher fields will be
       added as fields in metadata object.
    """

    url = baseAPI + "/vouchers/importCSV"
    headers = {'X-App-Id': configs['voucherify']['appId'],
               'X-App-Token': configs['voucherify']['appToken']}

    try:
        response = requests.post(url, headers=headers, files={'file': open(path ,'rb')})
        if response.status_code is 202:
            print("Imported vouchers from %s" % path)
        else:
            print("Failed to import vouchers from %s: %s" % (path,response.text))
    except BaseException as e:
        print("Failed to import vouchers from %s: %s" % (path,e))



def getRedemptionId(voucher):
    """Given a voucher, return its redemption ID"""

    url = baseAPI + "/vouchers/%s/redemption" % voucher

    response = requests.get(url, headers=headers)

    for red in response.json()['redemption_entries']:
        if red['result'] == "SUCCESS" and red['object'] == "redemption":
            return red['id']


def rollbackRedeem(voucher):
    """Undo voucher redemption"""

    url = baseAPI + "/redemptions/%s/rollback" % getRedemptionId(voucher)

    return requests.post(url, headers=headers).text


def redeemVoucher(voucher):
    """Redeem voucher"""
    url = baseAPI + "/vouchers/%s/redemption" % voucher

    return requests.post(url, headers=headers).text


def updateVoucher(voucher, amount=None, services=None, last_usage=None, redeem=None):
    """Updates  a voucher"""

    url = baseAPI + "/vouchers/metadata"
    data = {
        "codes": [voucher],
        "metadata": {}
    }

    if redeem is True:
        redeemVoucher(voucher)
    if amount is not None:
        data['metadata']['spent'] = amount
    if services is not None:
        data['metadata']['services'] = services
    if last_usage is not None:
        data['metadata']['last_usage'] = last_usage

    #print("Updating code %s with: %s" % (voucher, data))
    return requests.post(url, headers=headers, data=json.dumps(data)).json()


def getAllVouchers(simplified=True):
    """Gets all voucherify.io's vouchers"""

    url = baseAPI + "/vouchers"
    response = requests.get(url, headers=headers).json()["vouchers"]
    if simplified is None:
        return response
    else:
        res = []
        for obj in response:
            customObj = {}
            customObj["Code"] = obj["code"]
            # ----------------------------------------------------------
            try:
                customObj["Provider"] = obj["category"]
            except:
                customObj["Provider"] = obj["metadata"]["Provider"]
            try:
                customObj["lastUsage"] = obj["metadata"]["last_usage"]
            except:
                customObj["lastUsage"] = None
            # ----------------------------------------------------------
            customObj["Value"] = obj["discount"]["amount_off"] / 100  # because voucherify adds two 0's
            customObj["Expiration Date"] = obj["expiration_date"]
            customObj["Redemption Deadline"] = obj["metadata"]["Redemption_Deadline"]
            customObj["Email"] = obj["metadata"]["Email"]
            customObj["Redeemed"] = obj["redemption"]["redeemed_quantity"] # TODO: use this to avoid repeating redemption so the "failed redemption" msgs are not showed on the dashboard
            # the following 3 are not really needed here
            customObj["Voucher Type"] = obj["type"]
            customObj["Discount Type"] = obj["discount"]["type"]
            customObj["Redemption Limit"] = obj["redemption"]["quantity"]
            res.append(customObj)
        return res
