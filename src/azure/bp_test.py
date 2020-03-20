#!/usr/bin/env python3

from azure.common.client_factory import get_client_from_cli_profile # CLI auth requires azure-cli-core
from azure.common.credentials import ServicePrincipalCredentials
from azure.mgmt.billing import BillingManagementClient # pip3 install azure-mgmt-billing
from azure.mgmt.consumption import ConsumptionManagementClient
import azure
import json
from aux import *
import sys


def getSingleBillingPeriods(billing_period_name):
    customBillingClient = get_client_from_cli_profile(BillingManagementClient, subscription_id=configs["azure"]["subscriptionID"]["cernOcre"])
    return customBillingClient.billing_periods.get(billing_period_name=billing_period_name, custom_headers=None, raw=False).as_dict()

def listBillingPeriods(subscription_id=None):
    """Get the Azure credit/consumption data"""

    res = []
    customBillingClient = get_client_from_cli_profile(BillingManagementClient, subscription_id=subscription_id)
    for i in customBillingClient.billing_periods.list(filter=None, skiptoken=None, top=None, custom_headers=None, raw=False):
        res.append(i.as_dict())
    return res



#print(json.dumps(listBillingPeriods(subscription_id=configs["azure"]["subscriptionID"]["cernOcre"])))
#print(json.dumps(getSingleBillingPeriods('/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/201910' % configs["azure"]["subscriptionID"]["cernOcre"])))


customBillingClient = get_client_from_cli_profile(BillingManagementClient, subscription_id=configs["azure"]["subscriptionID"]["cernOcre"])

#print(customBillingClient.billing_periods.get(billing_period_name="201909-1", custom_headers=None, raw=False).as_dict())
#sys.exit(1)

bpName = '/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/201910' % configs["azure"]["subscriptionID"]["cernOcre"]

# NOTE: if the billing period does not have a '/' (starting does not count) it returns 400. If it has it returns 404. Always raises ErrorResponseException
#   Doing '' I see msrest.http_logger : Request URL: 'https://management.azure.com/subscriptions/54f623f0-8c18-40dd-9530-d32d2f1ee14f/providers/Microsoft.Billing/billingPeriods/201908?api-version=2018-03-01-preview'
#   so the name should not contain all the subscriptions/bla/bla  ?
bpNames = ['2019/06',
        '/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/201910' % configs["azure"]["subscriptionID"]["cernOcre"],
        'subscriptions/%s/providers/Microsoft.Billing/billingPeriods/201910' % configs["azure"]["subscriptionID"]["cernOcre"],
        '201906',
        '20191001',
        '/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/2019' % configs["azure"]["subscriptionID"]["cernOcre"],
        '/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/201908' % configs["azure"]["subscriptionID"]["cernOcre"],
        '/subscriptions/providers/Microsoft.Billing/billingPeriods/201908',
        '/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/' % configs["azure"]["subscriptionID"]["cernOcre"],
        '/subscriptions/%s/providers/Microsoft.Billing/billingPeriods' % configs["azure"]["subscriptionID"]["cernOcre"],
        'test',
        '',
        ' ',
        '  ',
        '    ',
        '  /  ',
        '/subscriptions/%s' % configs["azure"]["subscriptionID"]["cernOcre"],
        '/providers/Microsoft.Billing/billingPeriods',
        'billingPeriods',
        'billingPeriods/',
        '/billingPeriods/',
        '/billingPeriods',
        '/',
        '2019/',
        '/2019',
        '/201910',
        '2019/10',
        '201909-1']


def bp():
    for bp in bpNames:
        print("Trying %s" % bp)
        print(customBillingClient.billing_periods.get(billing_period_name=bp, custom_headers=None, raw=False).as_dict())
        print("Works %s" % bp)

    for bp in bpNames:
        try:
            print(customBillingClient.billing_periods.get(billing_period_name=bp, custom_headers=None, raw=False).as_dict())
            print("works %s" % bp)
        except azure.mgmt.billing.models.error_response.ErrorResponseException as e:
            print(bp)
            print("ErrorResponseException:")
            print(e)
            print("------------------------------------------------------")
        except BaseException as e:
            print(bp)
            print(e)
            print("------------------------------------------------------")


supportedAPIs = ["2017-04-24-preview",  # azure.mgmt.consumption.models.error_response_py3.ErrorResponseException: (UnsupportedSubscriptionType) Offer id MS-AZR-0111P is not supported.
                 "2017-06-30-preview",
                 "2018-03-01-preview",
                 "2018-11-01-preview",
                 "2018-12-01-preview",
                 "2019-04-01-preview",
                 "2019-05-01-preview",
                 "2019-01-01",
                 "2017-11-30",
                 "2018-01-31",
                 "2018-03-31",
                 "2018-05-31",
                 "2018-06-30",
                 "2018-08-31",
                 "2018-10-01",
                 "2019-05-01",
                 "2019-10-01",
                 "2019-11-01"]


subscription_id = configs["azure"]["subscriptionID"]["azureInOpen"]
theTool = get_client_from_cli_profile(ConsumptionManagementClient, subscription_id=subscription_id).usage_details
res = []
for i in theTool.list('/subscriptions/%s' % subscription_id, expand="properties/additionalInfo", filter=None, skiptoken=None, top=None, metric=2, custom_headers=None, raw=False):
    res.append(i.as_dict())
print(json.dumps(res))
sys.exit()


# APIs stuff
for api in supportedAPIs:
    theTool.api_version = api
    try:
        print("trying " + api)
        res = []
        for i in theTool.list(filter=None, skiptoken=None, top=None, custom_headers=None, raw=False):
            res.append(i.as_dict())
        print(res)
        print("------------------------------------------------------------")
    except BaseException as e:
        print("")
        print("Failed %s" % api)
        print(e)
        print("")
        print("------------------------------------------------------------")
