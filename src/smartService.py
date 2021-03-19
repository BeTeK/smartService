#!/usr/bin/python3

import cgitb
import cgi
import json
import os
import config
import MySql

if config.debug:
  cgitb.enable()

print("Content-Type: text/html")
print()

def getDevices(db):
  return db.getDevices()

def getSeries(db, parameterId, startTime, endTime, devices):
  return db.getSeries(parameterId, startTime, endTime, devices)

def generateError(txt):
  return {"result": "failed", "reason" : txt}

def main():
  form = cgi.FieldStorage()
  functionName = form["function"].value
  db = MySql.MySql(config.MySqlServer, config.MySqlDatabase, config.MySqlUsername, config.MySqlPassword)
  if functionName == "getDevices":
    return getDevices(db)
  elif functionName == "getSeries":
    devices = []
    if "deviceIdCount" not in form:
      return generateError("need parameter deviceIdCount")
      
    for i in range(int(form["deviceIdCount"].value)):
      paramKey = "deviceId_{0}".format(i)
      if paramKey not in form:
        return generateError("need parameter {0}".format(paramKey))
     
      devices.append(int(form["deviceId_{0}".format(i)].value))

    if "parameterId" not in form:
      return generateError("need parameter parameterId")

    if "startTime" not in form:
      return generateError("need parameter startTime")

    if "endTime" not in form:
      return generateError("need parameter endTime")
    
    parameterId = int(form["parameterId"].value)
    startTime = int(form["startTime"].value)
    endTime = int(form["endTime"].value)

    return getSeries(db, parameterId, startTime, endTime, devices)
  else:
    return generateError("unknown query {0}".format(functionName))

retVal = main()
if config.debug:
  print(json.dumps(retVal, indent=2, sort_keys=True))
else:
  print(json.dumps(retVal))
