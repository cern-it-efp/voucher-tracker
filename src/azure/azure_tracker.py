#!/usr/bin/env python3

# check this https://docs.microsoft.com/en-us/azure/billing/billing-usage-rate-card-overview

# auth https://docs.microsoft.com/en-us/azure/python/python-sdk-azure-authenticate#mgmt-auth-token

# CLI auth requires azure-cli-core
from azure.common.client_factory import get_client_from_cli_profile
from azure.common.credentials import ServicePrincipalCredentials
# pip3 install azure-mgmt-consumption
from azure.mgmt.consumption import ConsumptionManagementClient
# pip3 install azure-mgmt-billing
from azure.mgmt.billing import BillingManagementClient
# pip3 install azure-mgmt-subscription
from azure.mgmt.subscription import SubscriptionClient
import json
from aux import *

metric = ["ActualCostMetricType", "AmortizedCostMetricType", "UsageMetricType"]

# credentials = ServicePrincipalCredentials(
#    client_id=configs["azure"]["clientID"], # Your service principal App ID
#    secret=configs["azure"]["secret"], # Your service principal password
#    tenant=configs["azure"]["tenant"] # Tenant ID for your Azure subscription
# )

# client = BillingManagementClient(credentials=credentials,
#                                           subscription_id=configs["azure"]["subscriptionID"]["azureInOpen"],
#                                           base_url=None)[source]

# NOTE: the subscriptions here can be later overriden
billingClient = get_client_from_cli_profile(
    BillingManagementClient, subscription_id=configs["azure"]["subscriptionID"]["cernOcre"])
consumptionClient = get_client_from_cli_profile(
    ConsumptionManagementClient, subscription_id=configs["azure"]["subscriptionID"]["cernOcre"])
subscriptionClient = get_client_from_cli_profile(
    SubscriptionClient, subscription_id=configs["azure"]["subscriptionID"]["cernOcre"])


def getSingleBillingPeriods(billing_period_name):
    return billingClient.billing_periods.get(billing_period_name=billing_period_name, custom_headers=None, raw=False).as_dict()


def listBillingPeriods(subscription_id=None, api_version=None):
    """Get the Azure credit/consumption data"""

    res = []
    billingTool = get_client_from_cli_profile(
        BillingManagementClient, subscription_id=subscription_id).billing_periods
    if api_version is not None:
        billingTool.api_version = api_version
    print(billingTool.api_version)
    for i in billingTool.list(filter=None, skiptoken=None, top=None, custom_headers=None, raw=False):
        res.append(i.as_dict())
    return res


def listSubscriptions():
    """Returns a list with all the subscriptions the authenticated account
       has."""

    res = []
    for s in subscriptionClient.subscriptions.list(custom_headers=None, raw=False):
        res.append(s.as_dict())
    return res


# TODO: get all billing periods (listBillingPeriods) for all the subscriptions
def consumption(subscription_id=None):
    """Get the Azure credit/consumption data
       subscription_id: optional, array of subscriptions"""

    # NOTE: the command 'az consumption usage list --subscription "Azure in Open"' returns json with more stuff than the SDK: it has pretaxCost and the sum of all those matches what is shown in the cost management dashboard at portal.azure.com

    # az-cli uses api-version=2018-01-31

    # azureInOpen shows stuff which has neither dates nor cost!

    # scopes = ['/subscriptions/%s' % configs["azure"]["subscriptionID"]["cernOcre"], '/subscriptions/%s' % configs["azure"]["subscriptionID"]["azureInOpen"]]
    # scopes = ['/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/201911'  % configs["azure"]["subscriptionID"]["azureInOpen"]] # fails for azureInOpen

    #scopes = []

    # if subscription_id is None:
    #    print("use all subscriptions")
    #    subscriptions = listSubscriptions()

    # TODO: this would only show the current month consumption, gotta throw in here the billingPerios (underneath) to see past months.
    scopes = []

    # TODO: THIS ONE FAILS FOR azureInOpen with "Offer id MS-AZR-0111P" is not supported
    for bp in listBillingPeriods(subscription_id=subscription_id): #,api_version="2017-04-24-preview"):
        scopes.append('/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/%s' %
                      (subscription_id, bp["name"]))


    scopes = ['/subscriptions/%s/providers/Microsoft.Billing/billingPeriods/%s' % (subscription_id, "201909")]

    res = []
    theTool = consumptionClient.usage_details

    theTool.api_version = "2019-04-01-preview"
    for scope in scopes:
        for i in theTool.list(scope, expand="properties/additionalInfo", filter=None, skiptoken=None, top=None, metric=metric, custom_headers=None, raw=False):  # takes too long!
            i = i.as_dict()
            if i["cost"] > 0:
                res.append(i)
    return res

    supportedAPIs = ["2017-04-24-preview",
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

    for api in supportedAPIs:
        theTool.api_version = api
        try:
            print("trying " + api)
            for scope in scopes:
                for i in theTool.list(scope, expand="properties/additionalInfo", filter=None, skiptoken=None, top=None, metric=2, custom_headers=None, raw=False):  # takes too long!
                    res.append(i.as_dict())
            # explanation of each field https://azuresdkdocs.blob.core.windows.net/$web/python/azure-mgmt-consumption/3.0.0/azure.mgmt.consumption.models.html#azure.mgmt.consumption.models.UsageDetail
            print(json.dumps(res))
            print(
                "------------------------------------------------------------------------------")
        except BaseException as e:
            print("Failed %s" % api)
            print(e)
            print(
                "------------------------------------------------------------------------------")
