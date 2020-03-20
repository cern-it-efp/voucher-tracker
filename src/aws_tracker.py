#!/usr/bin/env python3

import boto3
import json
import os
import csv
from datetime import date
from aux import *
from zipfile import ZipFile
import time

# ------------------------------------------------------------------------------
# STEPS:
# 1 - Researcher creates an AWS account
# 2 - Researcher tells us the email used for the AWS account
# 3 - We add the researcher to the AWS organization using the email he provided
# 4 - We send the researcher the voucher for AWS
# 5 - The researcher redeems the AWS code and starts using stuff
# 6 - We can see the researcher's AWS consumption on the consolidated billing
# ------------------------------------------------------------------------------

# retrieve cost explorer API data at this level (all researchers getting a AWS voucher have to provide their aws account so they are linked to the organization)
organizationID = "o-b8rke7awm7"

creditsFilter = ["PS_POC_FY2019_Q3_GEANT_Netherlands","USE_FY2018_Q4-High-Performance-Computing-on-AWS"] # "USE_FY2018_Q4-High-Performance-Computing-on-AWS"

# when using 2010 complains "start date more than 12 months ago"
startDate = '2019-05-01T00:00:00Z'
startDate = '2019-10-01T00:00:00Z'
startDate = '2019-05-01'

# when using 2020 complains "end date past the beginning of next month"
endDate = '2019-10-20T00:00:00Z'
endDate = str(date.today())  # The daily cost for today wont be shown, but I believe the HOURLY one would do the job. Why can't I use that Granularity? The monthly shows more or less the same the daily one shows with the current filtering+GroupBy

# to retrieve the AWS bill for the current month at https://console.aws.amazon.com/billing/rest/v1.0/bill/completebill?month=CURRENT_MONTH&year=2019
currentMonth = date.today().month


def getClient(api):
    """"""
    return boto3.client(
        api,
        aws_access_key_id=configs["aws"]["accessKey"],
        aws_secret_access_key=configs["aws"]["secretKey"],
        region_name="us-east-1"
    )


def listAccounts(onlyActive=False):
    """"""
    if onlyActive is True:
        activeAccs = []
        for acc in getClient('organizations').list_accounts()["Accounts"]:
            if acc["Status"] == "ACTIVE":
                activeAccs.append(acc)
        return activeAccs
    else:
        return getClient('organizations').list_accounts()["Accounts"]


def aws_get_dim_values(op):
    """"""
    return getClient('ce').get_dimension_values(TimePeriod={
        'Start': startDate,
        'End': endDate
    }, Dimension=op)  # SUBSCRIPTION_ID # RECORD_TYPE


def listReportsBucket():
    """Gets the content in the bucket hosting the Cost and Usage reports"""

    return getClient('s3').list_objects(Bucket='voucher-usage-report')["Contents"]


def getAllData(useCE=False, filter=True, credits=None):
    """Gets the billing data. If useCE is True, uses the Cost Explorer API.
       Otherwise uses Cost And Usage Exportes: Downloads the latest report from
       the bucket 'voucher-usage-report' and gets the needed data from it"""

    if useCE is True:
        response = getClient('ce').get_cost_and_usage(
            TimePeriod={
                'Start': startDate,
                'End': endDate
            },
            Granularity='DAILY',
            Filter={
                'Dimensions': {
                    'Key': 'RECORD_TYPE',
                    'Values': [
                        'Credit',
                    ]
                }
            },
            Metrics=[
                'UnblendedCost',  # 'BlendedCost', 'AmortizedCost', 'NetAmortizedCost',  'NetUnblendedCost',  'NormalizedUsageAmount', 'UsageQuantity'
            ],
            GroupBy=[  # TODO: get the credit with smth like this?
                {
                    'Type': 'DIMENSION',
                    'Key': 'SERVICE'  # Valid values are AZ, INSTANCE_TYPE, LEGAL_ENTITY_NAME, LINKED_ACCOUNT, OPERATION, PLATFORM, PURCHASE_TYPE, SERVICE, TAGS, TENANCY, USAGE_TYPE
                },
                {
                    'Type': 'DIMENSION',
                    'Key': 'LINKED_ACCOUNT'  # 'REGION' # LINKED_ACCOUNT would show the AWS Account ID. From https://console.aws.amazon.com/organizations/home#/accounts I can map IDs with emails and account names, use https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/organizations.html#Organizations.Client.list_accounts
                }
            ]
        )

        filtered = []

        # TODO: any way to filter out estimated:true instead of 'by hand'?
        for obj in response['ResultsByTime']:
            if len(obj['Groups']) > 0 and float(obj['Groups'][0]['Metrics']['UnblendedCost']['Amount']) < 0:
                filtered.append(obj)
            elif obj['Estimated'] is False and float(obj['Total']['UnblendedCost']['Amount']) < 0:
                filtered.append(obj)

        res = {
            'ResultsByTime': filtered,
            'ResponseMetadata': response['ResponseMetadata']
        }

        return filtered

    orgAccounts = listAccounts() # TODO: will this user list be used in some other function? if so, has to be outside this function (global)
    client = getClient('s3')
    allReports = []  # there is a report for each month, get all and concat

    for obj in listReportsBucket():
        # TODO: slected "Overwrite existing report" but will it keep it from month to month or will each report (overriden) have ALL months since "opted in" and obj["LastModified"] > latest["LastModified"]:
        if "csv.zip" in obj["Key"]:
            allReports.append(obj["Key"])

    reportComplete = []

    for key in allReports:

        csvReportPath = os.path.basename(key)

        client.download_file('voucher-usage-report', key, csvReportPath)

        ZipFile(csvReportPath).extractall()

        # Print this report to see the whole list of returned fields (huge)
        reportComplete += list(csv.DictReader(open(csvReportPath[:-4])))
        # print(json.dumps(reportComplete,default=str))

        #lineItem/UsageStartDate\": \"2019-10-23T15:00:00Z\", \"lineItem/UsageEndDate\": \"2019-10-29T17:00:01Z

        # cleanup:remove both .zip and .csv files
        os.remove(csvReportPath)
        os.remove(csvReportPath[:-4])

    res = []
    fields = ["identity/TimeInterval", "bill/PayerAccountId",
              "bill/BillingPeriodStartDate", "bill/BillingPeriodEndDate",
              "lineItem/UsageAccountId", "lineItem/LineItemType",
              "lineItem/UsageStartDate", "lineItem/UsageEndDate",
              "lineItem/CurrencyCode", "lineItem/UnblendedCost",
              "lineItem/LineItemDescription", "product/ProductName",
              "product/region", "product/servicecode", "product/servicename",
              "pricing/term", "product/instanceType", "product/memory",
              "product/operatingSystem", "product/physicalProcessor",
              "product/processorFeatures", "product/vcpu"]

    if filter is False:
        res = reportComplete
    else:
        for obj in reportComplete:
            if obj["lineItem/LineItemType"] == "Credit":
                filteredObj = {}
                currentAccount = [d for d in orgAccounts if d["Id"] == obj["lineItem/UsageAccountId"]][0]
                filteredObj["lineItem/UsageAccountUsername"] = currentAccount["Name"]
                filteredObj["lineItem/UsageAccountEmail"] = currentAccount["Email"]

                for field in fields:
                    try:
                        filteredObj[field] = obj[field]
                    except:
                        pass
                res.append(filteredObj)

    if credits is not None:
        filteredSpecificCredits = []
        for obj in res:
            if obj["lineItem/LineItemDescription"] in credits:
                filteredSpecificCredits.append(obj)
        res = filteredSpecificCredits

    return res


def getVouchers(useCE=False):
    """Gets all the billing data and groups it by vouchers"""

    vouchers = []

    for acc in listAccounts(onlyActive=True):

        voucher = {}
        voucher["accountID"] = acc["Id"]
        voucher["Email"] = acc["Email"]
        voucher["Name"] = acc["Name"]
        voucher["lastUsage"] = ""
        voucher["spent"] = 0
        services = set()

        if useCE is True:

            for entry in getAllData(useCE=True):
                if acc["Id"] == entry["Groups"][0]["Keys"][1]:
                    services.add(entry["Groups"][0]["Keys"][0])
                    voucher["lastUsage"] = entry["TimePeriod"]["End"] if entry["TimePeriod"]["End"] > voucher["lastUsage"] else voucher["lastUsage"]
                    voucher["spent"] += float(entry["Groups"][0]["Metrics"]["UnblendedCost"]["Amount"])

            voucher["services"] = list(services)
            vouchers.append(voucher)

        else:

            credits = set()
            locations = set()

            for entry in getAllData():
                if acc["Id"] == entry["lineItem/UsageAccountId"] and entry["lineItem/LineItemDescription"] in creditsFilter:
                    try:
                        if entry["product/instanceType"] is None:
                            services.add("%s - %s" % (entry["product/servicename"], entry["product/instanceType"]))
                        else:
                            services.add(entry["product/servicename"])
                    except:
                        services.add(entry["product/servicename"])
                    locations.add(entry["product/region"])
                    voucher["lastUsage"] = entry["lineItem/UsageEndDate"] if entry["lineItem/UsageEndDate"] > voucher["lastUsage"] else voucher["lastUsage"]
                    voucher["spent"] += float(entry["lineItem/UnblendedCost"])
                    credits.add(entry["lineItem/LineItemDescription"])


            voucher["services"] = list(services)
            voucher["location"] = list(locations)
            voucher["credits"] = list(credits)
            vouchers.append(voucher)

    return vouchers
