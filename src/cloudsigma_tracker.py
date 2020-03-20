#!/usr/bin/env python3

import json
import time
import collections
import os
import requests
import sys
from aux import *
from enum import Enum

Location = Enum('Location', 'dub fra gva mnl mia mel hnl per ruh sjc tyo wdc zrh')

def baseEndpoint(location,specificAPI):
    return "https://%s.cloudsigma.com/api/2.0/%s" % (location,specificAPI)

encodedCreds = "1234abcd"

def getVoucher():
    """Gets all the billing data and groups it by vouchers"""

specificAPI = "balance"
specificAPI = "subscriptions"
endpoint = baseEndpoint("gva",specificAPI)

response = requests.get(endpoint, headers={'Authorization': 'Basic %s' % encodedCreds})

print(response.text)
