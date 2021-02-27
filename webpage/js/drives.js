"use strict";

function createGraphTypeOptions(){
  var graphType = $("<select/>")
  graphType.attr("name", "graphType");
  graphType.attr("id", "graphType");
  
  var parameterSelection = $("<option/>");
  parameterSelection.attr("value", "parameter");
  parameterSelection.text("Parameters");
  graphType.append(parameterSelection);
  
  var driveSelection = $("<option/>");
  driveSelection.attr("value", "drive");
  driveSelection.text("Drives");
  graphType.append(driveSelection);
  
  return graphType;
}

function intersection(setA, setB) {
    let _intersection = new Set()
    for(let elem of setB) {
        if (setA.has(elem)) {
            _intersection.add(elem)
        }
    }
    return _intersection
}

function getCommonSmartParameters(driveData, selectedDrives, parametersEl){
  var commonParameters = new Set();
  var first = true;
  for(var driveIndex of selectedDrives){
    if(first){
      commonParameters = new Set(driveData.devices[driveIndex].parametersIds);
      first = false;
    }
    else{
      commonParameters = intersection(commonParameters, new Set(driveData.devices[driveIndex].parametersIds));
    }
  }

  var ret = [];
  for(var paramIndex of commonParameters){
    ret.push({"paramId" : paramIndex,
              "name" : driveData.parameters[paramIndex].name,
              "smartId" : driveData.parameters[paramIndex].smartId});
  }
  return ret;
}

function updateParameters(service, chart, driveData, selectedDrives, parametersEl){
  var commonParameters = getCommonSmartParameters(driveData, selectedDrives, parametersEl);
  parametersEl.empty();
  var parametersListEl = $("<li/>");
  
  var index = 0;
  for(var parameter of commonParameters){
    var listItem = $("<ul/>");
    parametersListEl.append(listItem);
    
    var radioId = "parameter_id_" + index;
    var radio = $("<input/>");
    radio.attr("type", "radio");
    radio.attr("id", radioId);
    radio.attr("name", "parameters");
    radio.val(parameter.paramId);
    
    var label = $("<label/>");
    label.attr("for", radioId);
    label.text(parameter.name);
    listItem.append(radio);
    listItem.append(label);

    radio.change(() => {
      var selected = $("input[name='parameters']:checked").val();
      updateGraph(service, chart, driveData, selectedDrives, selected);
    });
    
    index += 1;
  }
  parametersEl.append(parametersListEl);
}

function convertTemperature(value){
  var raw = value.raw;
  return raw & 0xff;
}

function convertDefault(value){
  var rawStr = value.rawString;
  var current = parseInt(rawStr);

  return current;
}

function selectDataConverter(smartId){
  if(smartId == 194){
    return convertTemperature;
  }
  else{
    return convertDefault;
  }
}

function updateGraph(service, chart, driveData, selectedDrives, selectedParameter){
  console.log(selectedDrives);
  console.log(selectedParameter);

  service.getSeries(new Date(0), new Date(), selectedParameter, selectedDrives).then(result => {
    var driveSeries = [];
    var dataConverterFn = selectDataConverter(driveData.parameters[selectedParameter].smartId);
    
    for(var driveIndex in result){
      var drive = driveData.devices[driveIndex];
      var data = [];
      for(var smartValue of result[driveIndex]){
        data.push([smartValue.timestamp, dataConverterFn(smartValue)]);
      }
      driveSeries.push({"name" : drive.modelFamily + " " + drive.serialNumber, "data" : data});
    }
    console.log(result);
    chart.updateSeries(driveSeries);
  });
}

function selectedDrivesAsList(drivesLst){
  var ret = [];

  for(var drive of drivesLst){
    if(drive.driveElement.is(':checked')){
      ret.push(drive.driveIndex);
    }
  }

  return ret;
}


function createDriveSelection(service, chart, driveData, drivesEl, parametersEl){
  drivesEl.empty();
  parametersEl.empty();
  var driveListEl = $("<li/>");
  var driveLst = [];
  
  $.each(driveData.devices, (index, value) => {
    var driveSelect = $("<input/>");
    
    driveSelect.change(() => {
      var selectedDrives = selectedDrivesAsList(driveLst);
      updateParameters(service, chart, driveData, selectedDrives, parametersEl);
    });
    
    var selectName = "drive_select_" + index;
    driveSelect.attr("type", "checkbox");
    driveSelect.attr("name", selectName)
    var driveLabel = $("<label/>");
    driveLabel.attr("for", selectName);
    driveLabel.text(value.modelFamily + " " + value.serialNumber);

    var listItem = $("<ul/>");
    listItem.append(driveSelect);
    listItem.append(driveLabel);
    driveListEl.append(listItem);
    driveLst.push({"driveIndex": index, "driveElement": driveSelect});
  });

  drivesEl.append(driveListEl);
}

function createParametersSelection(service, chart, driveData, parametersEl, drivesEl){
  drivesEl.empty();
  parametersEl.empty();
}
function createChart(){
  var options = {
    series: [],
    chart: {
      type: 'area',
      stacked: false,
      height: 350,
      zoom: {
        type: 'x',
        enabled: true,
        autoScaleYaxis: true
      },
      toolbar: {
        autoSelected: 'zoom'
      }
    },
    dataLabels: {
      enabled: false
    },
    markers: {
      size: 0,
    },
    title: {
      text: 'Smart parameter',
      align: 'left'
    },
    fill: {
      type: 'gradient',
      gradient: {
        shadeIntensity: 1,
        inverseColors: false,
        opacityFrom: 0.5,
        opacityTo: 0,
        stops: [0, 90, 100]
      },
    },
    yaxis: {
      labels: {
        formatter: function (val) {
          return val;
        },
      },
      title: {
        text: "Smart"
      },
    },
    xaxis: {
      type: 'datetime',
    },
    tooltip: {
      shared: false,
      y: {
        formatter: function (val) {
          return val;
        }
      }
    },
    noData: {
      text: 'Select drives and parameter'
    }
  };
  
  var chart = new ApexCharts(document.querySelector("#chart"), options);
  chart.render();
  return chart;
}

function setGraphOptions(service, chart, driveData){
  var graphType = createGraphTypeOptions()
  graphType.change(function(eventObj){
    $("#drives").empty();
    $("#parameters").empty();
    
    var type = $(eventObj.currentTarget).val();
    if(type == "drive"){
      createDriveSelection(service, chart, driveData, $("#drives"), $("#parameters"));
    }
    else if(type == "parameters"){
      createParametersSelection(service, chart, driveData, $("#drives"), $("#parameters"));
    }
    else{
      
    }
  });
  $("#type").append(graphType);
}

$(document).ready(function(){
  var service = SmartService();
  var chart = createChart();
  service.getDevices().then(result => setGraphOptions(service, chart, result));
  //  var series = service.getSeries(new Date(0), new Date(), 1, [1,2]);
//  Promise.all([devices, series]).then(results => {
//    console.log(results[0]);
//    console.log(results[1]);
//  });
  
});
