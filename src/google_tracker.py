#!/usr/bin/env python3

import json
import time
import collections
import os
from google.cloud import bigquery
# pip3 install --upgrade google-cloud-resource-manager
from google.cloud import resource_manager
from google.cloud.bigquery import dbapi
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2 import service_account
from aux import *
import sys

GCPcredentials = service_account.Credentials.from_service_account_file(configs["google"]["serviceAccountFile"])

ignacioATarchiver_table = "ocrets.billing_export.gcp_billing_export_v1_01138D_6F3F18_69D7A4"
pb2_table = "stoked-archway-255209.billing.gcp_billing_export_v1_01FEFA_5CCFF4_D60F13"

BQtable = pb2_table


def getQuery(table):
    """Returns the SELECT query for the given table."""

    return (
        "SELECT service.description AS service_description, sku.description AS sku_description, usage_start_time, usage_end_time, c.name AS voucher, c.amount, export_time"
        " FROM `%s`, UNNEST(credits) AS c"
        " WHERE c.amount < 0" % table
    )


# Location must match that of the dataset(s) referenced in the query.
tableLocation = "europe-north1"


def BQclient(project=None):
    """Returns a client for the specified project. If no project is specified
       the default one will be used."""
    if project is None:
        GCPcredentials = configs["google"]["serviceAccountFile"]
        return bigquery.Client.from_service_account_json(GCPcredentials)
    GCPcredentials = service_account.Credentials.from_service_account_file(configs["google"]["serviceAccountFile"])
    return bigquery.Client(credentials=GCPcredentials, project=project)


def listProjects():
    """List projects"""

    GCPcredentials = service_account.Credentials.from_service_account_file(configs["google"]["serviceAccountFile"])
    return resource_manager.Client(credentials=GCPcredentials).list_projects()


def getAllData(table):
    """Get the Google credit/consumption data. The fields the objects returned
       by this function have depend on the SELECT query defined above."""

    query_job = BQclient().query(  # TODO: takes always 4:23 minutes to complete
        getQuery(table) # , location=tableLocation  # TODO: needed?
    )

    objects_list = []
    f = '%Y-%m-%d %H:%M:%S'
    for row in query_job:
        d = collections.OrderedDict()
        d['service_description'] = row.service_description
        d['sku_description'] = row.sku_description
        d['voucher'] = row.voucher
        d['amount'] = row.amount
        d['usage_start_time'] = row.usage_start_time.strftime(f)
        d['usage_end_time'] = row.usage_end_time.strftime(f)
        # TODO: use this to filter data: only feed voucherify with data that it doesn't have yet?
        d['export_time'] = row.export_time.strftime(f)
        objects_list.append(d)
    return objects_list


def getRemaining(voucher, initialAmount, useBQ=False, data=None):
    """Returns the remaining amount for the given voucher.
       Uses the BigQuery by default. Otherwise relies on getAllData."""

    res = initialAmount  # TODO: assuming here the voucher is for 1000. But there will be also vouchers for 3000
    if data is None:
        if useBQ is True:
            query = (
                "SELECT SUM(c.amount) AS consumed"
                " FROM `ocrets.billing_export.gcp_billing_export_v1_01138D_6F3F18_69D7A4`,"
                " UNNEST(credits) as c WHERE c.amount < 0 AND c.name = \"%s\"" % voucher
            )

            query_job = BQclient().query(  # TODO: takes always 4:23 minutes to complete
                query,
                location=tableLocation
            )
            for row in query_job:
                return res + row.consumed

        else:
            data = getAllData()
            for obj in data:
                if obj['voucher'] == voucher:
                    res += obj['amount']
            return res
    else:
        for obj in data:
            if obj['voucher'] == voucher:
                res += obj['amount']
        return res


def plainVouchers(dict):
    """Returns a list with the vouchers on the dict"""
    res = []
    for obj in dict:
        res.append(obj['voucher'])
    return res


def getRedeemedVouchers():  # TODO: this calls getAllData which iterates once and then does another iteration over data 'for obj in data'
    """Returns a dict containing the redeemed vouchers and their remaining credit"""
    res = []
    data = getAllData()
    for obj in data:
        newVoucher = collections.OrderedDict()
        if obj['voucher'] not in plainVouchers(res):
            newVoucher['voucher'] = obj['voucher']
            newVoucher['remaining_amount'] = getRemaining(
                obj['voucher'], 1000, data=data)
            res.append(newVoucher)
    return json.dumps(res)


def listDatasets(client=None, project=None, onlyIDs=True):
    """List datasets"""

    datasets = list(client.list_datasets(project=project))

    resDatasets = []

    if datasets:
        for dataset in datasets:
            if onlyIDs is True:
                resDatasets.append(dataset.dataset_id)
            else:
                resDatasets.append(dataset)

    return resDatasets


def getAllTables():
    """Returns all the GCP billing export tables the authenticated user has
       access (view) to."""

    tablesIDs = []
    for p in listProjects():
        client = BQclient(project=p.project_id)
        for ds in listDatasets(client=client, project=p.project_id):
            for tableListItem in client.list_tables(ds):
                if "gcp_billing_export" in tableListItem.full_table_id:
                    tablesIDs.append(tableListItem.full_table_id.replace(':','.'))
    return tablesIDs


def toVoucher(billingData):
    """Groups billing data into a single object representing a voucher"""

    voucher = {}
    voucher["code"] = billingData[0]["voucher"]
    voucher["lastUsage"] = ""
    voucher["spent"] = 0
    services = set()

    for entry in billingData:
        services.add("%s" % entry["sku_description"])
        voucher["lastUsage"] = entry["usage_start_time"] if entry["usage_start_time"] > voucher["lastUsage"] else voucher["lastUsage"]
        voucher["spent"] += float(entry["amount"])

    voucher["services"] = list(services)

    return voucher


def getVouchers():
    """Gets all the billing data and groups it by vouchers"""

    vouchers = []
    for t in getAllTables():
        voucher = toVoucher(getAllData(t))
        vouchers.append(voucher)
    return vouchers
