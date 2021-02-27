"use strict";

function SmartService(){
  var serviceUrl = "https://btk.serv.fi/cgi-bin/smartCollect/smartService.py";
  var getDevices = async function(){
    return new Promise(resolve => {
      $.getJSON(serviceUrl, {"function": "getDevices"}, function(res){
        resolve(res);
      });
    });
  };

  var getSeries = async function(startTime, endTime, parameterId, deviceList){
    var data = {"function": "getSeries",
                "startTime": Math.floor(startTime.getTime() / 1000),
                "endTime": Math.floor(endTime.getTime() / 1000),
                "parameterId": parameterId,
                "deviceIdCount": deviceList.length};
    $.each(deviceList, function(index, value){
      data["deviceId_" + index] = value;
    });
    
    return new Promise(resolve => {
      $.getJSON(serviceUrl, data, function(res){
        for(var deviceParamValues in res){
          for(var val of res[deviceParamValues]){
            val.timestamp = new Date(val.timestamp * 1000);
          }
        }
        resolve(res);
      });
    });
  };

  return {
    "getDevices" : getDevices,
    "getSeries" : getSeries
  };
};
