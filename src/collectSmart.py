#!/usr/bin/python3

import re
import subprocess
import json
import MySql
import config

def collectData(devs):
  for dev in devs:
    with subprocess.Popen(["smartctl", "-a", "-j", dev], stdout=subprocess.PIPE, stderr=subprocess.PIPE) as process:
      outs = process.stdout.read().decode("UTF-8")
      yield json.loads(outs)

def convertParamToDB(param):
  return MySql.ParameterValue(param["id"],
                              param["name"],
                              param["value"],
                              param["worst"],
                              param["thresh"] if "thresh" in param else -1,
                              param["raw"]["value"],
                              param["raw"]["string"])
      


def main():
  db = MySql.MySql(config.MySqlServer, config.MySqlDatabase, config.MySqlUsername, config.MySqlPassword)
  v = list(collectData(config.devices))
  for i in v:
    device = MySql.Device(i["model_name"], i["model_family"] if "model_family" in i else "no family", i["serial_number"])
    params = [convertParamToDB(p) for p in i["ata_smart_attributes"]["table"]]
    db.addMeasurement(device, params)

if __name__ == "__main__":
  main()



