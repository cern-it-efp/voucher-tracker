#!/usr/bin/env python3

# TODO: create a mongoDB on another pod (inside the same node as it will be a single node k8s cluster), and store there the consumption.
#       This way the voucher-tracker does not have to get all the consumption on each iteration, just the one for the last few days. With that plus what's inside the DB updates voucherify.

import pymongo

print("creating client...")
client = pymongo.MongoClient("mongodb://localhost:27017/")
print("client created...")

voucherTrackerDB = client["voucherTrackerDB"]

googleCol = voucherTrackerDB["googleCol"]
awsCol = voucherTrackerDB["awsCol"] # includes resellers (TISparkle)
azureCol = voucherTrackerDB["azureCol"] # includes resellers (Micromail)
exoscaleCol = voucherTrackerDB["exoscaleCol"]
cloudSigmaCol = voucherTrackerDB["cloudSigmaCol"]
cloudFerroCol = voucherTrackerDB["cloudFerroCol"]

def insert(dict, collection):
    #mydict = { "name": "Peter", "address": "Lowstreet 27" }
    #x = collection.insert_one(mydict)
    x = collection.update(document=dict, upsert=True)
    print(x.inserted_id)

#print(client.list_database_names())

print("run find()...")
for x in mycol.find():
  print(x)
