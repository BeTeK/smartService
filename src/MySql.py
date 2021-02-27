import MySQLdb
import time

class Device:
  def __init__(self, modelName, modelFamily, serialNumber):
    self._modelName = modelName
    self._modelFamily = modelFamily
    self._serialNumber = serialNumber

  def getModelName(self):
    return self._modelName

  def getModelFamily(self):
    return self._modelFamily

  def getSerialNumber(self):
    return self._serialNumber

  def __str__(self):
    return "Device(modelName = {0}, modelFamily = {0}, serialNumber = {0})".format(self._modelName, self._modelFamily, self._serialNumber)

class ParameterValue:
  def __init__(self, smartParamId, paramName, value, worst, thresh, raw, rawString):
    self._smartParamId = smartParamId
    self._paramName = paramName
    self._value = value
    self._worst = worst
    self._thresh = thresh
    self._raw = raw
    self._rawString = rawString

  def getSmartParamId(self):
    return self._smartParamId
    
  def getParamName(self):
    return self._paramName
    
  def getValue(self):
    return self._value
    
  def getWorst(self):
    return self._worst
    
  def getThresh(self):
    return self._thresh
    
  def getRaw(self):
    return self._raw
    
  def getRawString(self):
    return self._rawString

  def __str__(self):
    return "ParameterValue(smartParamId = {0}, paramName = {1}, value = {2}, worst = {3}, thresh = {4}, raw = {5}, rawString = {6})".format(self._smartParamId, self._paramName, self._value, self._worst, self._thresh, self._raw, self._rawString)

class MySql:
  def __init__(self, server, dbName, username, password):
    self.db = MySQLdb.connect(server, username, password, dbName)

  def _doQuery(self, queryFn, retryCount = 999999):
    lastException = None
    for i in range(retryCount):
      c = None
      try:
        c = self.db.cursor()
        result = queryFn(c)
        self.db.commit()
        lastException = None
        return result
      except Exception as ex:
        self.db.rollback()
        lastException = ex
      finally:
        if c is not None:
          c.close()
          c = None

    if lastException is not None:
      raise lastException

  def _fetchOrGenerateDeviceId(self, c, device):
    c.execute("SELECT Devices.id FROM Devices WHERE Devices.serialNumber = %s", (device.getSerialNumber(), ))
    deviceId = c.fetchone()
    if deviceId is None:
      c.execute("INSERT INTO Devices (modelName, ModelFamily, serialNumber) VALUES (%s, %s, %s)", (device.getModelName(), device.getModelFamily(), device.getSerialNumber(), ))
      deviceId = c.lastrowid
    else:
      deviceId = deviceId[0]

    return deviceId
    
  def _fetchOrGenerateParameterIds(self, c, parameters):
    smartParamIds = [p.getSmartParamId() for p in parameters]
    paramStrLst = ", ".join("%s" for i in parameters)
    c.execute("SELECT Parameters.id as id, Parameters.smartParamId as smartId FROM Parameters WHERE Parameters.smartParamId IN (" + paramStrLst + ")", smartParamIds)
    
    paramsInTheDB = dict((i[1], i[0]) for i in c.fetchall())
    alreadyInTheDB = paramsInTheDB.keys()
    missingFromTheDb = [i for i in parameters if i.getSmartParamId() not in alreadyInTheDB]

    for param in missingFromTheDb:
      smartId = param.getSmartParamId()
      c.execute("INSERT INTO Parameters(smartParamId, name) VALUES (%s, %s)", (smartId, param.getParamName(), ))
      dbId = c.lastrowid
      paramsInTheDB[smartId] = dbId

    return paramsInTheDB

  def _addParameters(self, c, deviceId, smartIds, parameters):
    now = int(time.time())
    sql = "INSERT INTO ParameterValues(parameterId, value, worst, thresh, raw, rawString, timestamp, devicesId) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)"
    values = [(smartIds[i.getSmartParamId()], i.getValue(), i.getWorst(), i.getThresh(), i.getRaw(), i.getRawString(), now, deviceId) for i in parameters]
    c.executemany(sql, values)

  def _addParameterToDeviceLinks(self, c, deviceId, smartIds):
    smartIdParams = ", ".join("%s" for i in smartIds)
    sql = "SELECT ParametersId FROM DeviceParameters WHERE devicesId = %s and ParametersId IN (" + smartIdParams + ")"
    c.execute(sql, [deviceId] + list(smartIds.values()))
    alreadyIdDb = [i[0] for i in c.fetchall()]
    missingFromDb = [i for i in smartIds.values() if i not in alreadyIdDb]
    if len(missingFromDb) > 0:
      values = [(deviceId, i) for i in missingFromDb]
      c.executemany("INSERT INTO DeviceParameters(devicesId, ParametersId) VALUES (%s, %s)", values)
    
  def _addMeasurementQuery(self, c, device, parameters):
    deviceId = self._fetchOrGenerateDeviceId(c, device)
    paramIds = self._fetchOrGenerateParameterIds(c, parameters)
    self._addParameterToDeviceLinks(c, deviceId, paramIds)
    self._addParameters(c, deviceId, paramIds, parameters)
    
  def addMeasurement(self, device, parameters):
    self._doQuery(lambda c: self._addMeasurementQuery(c, device, parameters), 1)

  def _getDevicesQuery(self, c):
    c.execute("SELECT id, modelName, modelFamily, serialNumber FROM Devices")
    result = dict([(i[0], {"modelName": i[1], "modelFamily": i[2], "serialNumber": i[3]}) for i in c.fetchall()])
    
    sqlParamsStr = ",".join("%s" for i in result.keys())
    c.execute("SELECT devicesId, ParametersId FROM DeviceParameters WHERE devicesId in (" + sqlParamsStr + ")", result.keys())
    parametersIds = set()
    for i in c.fetchall():
      if "parametersIds" not in result[i[0]]:
        result[i[0]]["parametersIds"] = []
      result[i[0]]["parametersIds"].append(i[1])
      parametersIds.add(i[1])

    sqlParamsStr = ",".join("%s" for i in parametersIds)
    c.execute("SELECT id, name, smartParamId FROM Parameters WHERE id IN (" + sqlParamsStr + ")", parametersIds)
    parameters = dict((i[0], {"name" : i[1], "smartId" : i[2]}) for i in c.fetchall())
    
    return {"parameters" : parameters, "devices" : result}
  
  def getDevices(self):
    return self._doQuery(lambda c: self._getDevicesQuery(c))

  def _getSeriesQuery(self, c, parameterId, startTime, endTime, devices):
    sql = "SELECT value, raw, timestamp, devicesId, rawString FROM ParameterValues WHERE parameterId = %s AND %s <= timestamp AND timestamp <= %s AND devicesId in (" + ",".join("%s" for i in devices) + ")"
    c.execute(sql, [parameterId, startTime, endTime] + devices)
    
    results = {}

    for i in c.fetchall():
      if i[3] not in results:
        results[i[3]] = []

      results[i[3]].append({"value": i[0], "timestamp": i[2], "raw" : i[1], "rawString" : i[4]})
    return results
  
  def getSeries(self, parameterId, startTime, endTime, devices):
    return self._doQuery(lambda c: self._getSeriesQuery(c, parameterId, startTime, endTime, devices))








    
