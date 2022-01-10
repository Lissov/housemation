import _thread
from time import sleep
import paho.mqtt.client as mqtt
import housemation, icontroller, indicators
import json
from datetime import datetime
import pushover
 
TOPIC_ROOT = "zigbee2mqtt/"
BROKER_ADDRESS = "0.0.0.0"
PORT = 1883
TOPIC_NetworkMap = TOPIC_ROOT + 'bridge/request/networkmap'
TOPIC_NetworkMap_GV = TOPIC_ROOT + 'bridge/response/networkmap'

class MqttDevice(housemation.Device):
    battery = None
    linkQuality = None
    indicator = indicators.Indicators()
    ledNumber = None
    def __init__(self, sensorId: str, typ, vendor, name: str):
        super().__init__(vendor, typ, sensorId, name)
    def processMessage(self, message, timestamp):
        msg = json.loads(message)
        self.battery = msg['battery'] if 'battery' in msg else None
        self.linkQuality = msg['linkquality'] if 'linkquality' in msg else None
        self.changedOn = datetime.utcnow()
        self.displayStatus()
    def displayStatus(self):
        pass
    def toServerObj(self):
        so = super().toServerObj()
        so['BatteryLevel'] = None if self.battery is None else int(round(self.battery))
        so['LinkQuality'] = self.linkQuality
        return so
    def execute(self, args):
        if len(args) >= 1 and (args[1] == 'on' or args[1] == 'off'):
            return (True, 'No on/off for sensor')
        return super().execute(args)
    def toOutstandingText(self):
        if self.isOpen:
            return self.name + ' is OPEN'
        return None

class MqttSensor(MqttDevice):
    isOpen = None
    humidity = None
    pressure = None
    temperature = None
    co2 = None
    formaldehyde = None
    voc = None
    leak = None
    notifyClose = False
    notifyOpen = False
    statusChangedOn = None
    def __init__(self, sensorId: str, typ, vendor, name: str):
        super().__init__(sensorId, typ, vendor, name)
    def processMessage(self, message, timestamp):
        msg = json.loads(message)
        newOpen = not msg['contact'] if 'contact' in msg else None
        newLeak = msg['water_leak'] if 'water_leak' in msg else None
        openClose = (self.isOpen is None and newOpen is not None) or (self.isOpen != newOpen)
        leaked = self.leak != newLeak
        self.isOpen = newOpen
        self.temperature = msg['temperature'] if 'temperature' in msg else None
        self.pressure = msg['pressure'] if 'pressure' in msg else None
        self.humidity = msg['humidity'] if 'humidity' in msg else None
        self.co2 = msg['co2'] if 'co2' in msg else None
        self.formaldehyde = msg['formaldehyd'] if 'formaldehyd' in msg else None
        self.voc = msg['voc'] if 'voc' in msg else None        
        self.leak = newLeak
        super().processMessage(message, timestamp)
        if openClose and ((newOpen and self.notifyOpen) or (not newOpen and self.notifyClose)):
            self.statusChangedOn = datetime.utcnow()  
            return self.name + ' is ' + ('OPEN' if newOpen else 'closed')
        if leaked:
            self.statusChangedOn = datetime.utcnow()
            return self.name + ' ' + ('DETECTED A LEAK' if newLeak else 'Detected no leak')
        else:
            return None
    def displayStatus(self):
        if (self.ledNumber is not None and self.ledNumber >= 0):
            if (self.isOpen is not None):
                self.indicator.showLed(self.ledNumber, self.isOpen)
            if (self.humidity is not None):
                self.indicator.showLed(self.ledNumber, self.humidity > 60)
    def getReminderText(self):
        if (self.notifyIntervalSec > 0 and (self.isOpen or self.leak) and self.statusChangedOn is not None):
            prevPoint = self.lastRemindedOn if (self.lastRemindedOn is not None and self.lastRemindedOn > self.statusChangedOn) else self.statusChangedOn
            delta = datetime.utcnow() - prevPoint
            deltaFromInit = datetime.utcnow() - self.statusChangedOn
            if (delta.seconds > self.notifyIntervalSec):
                self.lastRemindedOn = datetime.utcnow()
                return self.name + ' is ' + ('OPEN' if self.isOpen else 'LEAKED') + ' since ' + str(round(deltaFromInit.seconds/60)) + ' minutes.'
        return None
    def toServerObj(self):
        so = super().toServerObj()
        if self.isOpen is not None:
            so['Open'] = self.isOpen
        if self.temperature is not None:
            so['humidity'] = self.humidity
            so['temperature'] = self.temperature
            so['pressure'] = self.pressure
        if self.co2 is not None:
            so['co2'] = self.co2
        if self.formaldehyde is not None:
            so['formaldehyde'] = self.formaldehyde
        if self.voc is not None:
            so['voc'] = self.voc
        if self.leak is not None:
            so['waterLeak'] = self.leak
        return so

class MqttBulb(MqttDevice):
    turnedOn = None
    brightnessLevel = None
    mqttClient: mqtt.Client = None
    def __init__(self, sensorId: str, typ, vendor, name: str, mqttClient: mqtt.Client):
        super().__init__(sensorId, typ, vendor, name)
        self.mqttClient = mqttClient
    def toServerObj(self):
        so = super().toServerObj()
        so['TurnedOn'] = self.turnedOn
        so['Brightness'] = self.brightnessLevel
        return so
    def toOutstandingText(self):
        if self.turnedOn:
            return self.name + ' is ON'
        return None
    def processMessage(self, message, timestamp):
        msg = json.loads(message)
        self.turnedOn = msg['status'] == 'ON' if 'status' in msg else msg['state'] == 'ON' if 'state' in msg else None
        self.brightnessLevel = msg['brightness'] if 'brightness' in msg else None
        super().processMessage(message, timestamp)
        return None
    def displayStatus(self):
        if (self.ledNumber is not None and self.ledNumber >= 0):
            if (self.turnedOn is not None):
                self.indicator.showLed(self.ledNumber, self.turnedOn)
    def askStatus(self):
        if self.mqttClient is not None:
            self.mqttClient.publish(TOPIC_ROOT + self.vendor_id + '/get', '{"state":""}')
    def execute(self, args):
        if len(args) >= 1 and (args[1] == 'on' or args[1] == 'off'):
            if self.mqttClient is not None:
                st = 'ON' if args[1] == 'on' else 'OFF'
                self.mqttClient.publish(TOPIC_ROOT + self.vendor_id + '/set', '{"state":"' + st + '"}')
                self.askStatus()
                return (True, 'Command sent to lapm. Check status to know how it is processed')
            else:
                return (False, 'MQTT client missing.')
        if len(args) >= 2 and (args[1] == 'brightness'):
            if self.mqttClient is not None:
                level = int(args[2])
                self.mqttClient.publish(TOPIC_ROOT + self.vendor_id + '/set', '{"brightness":' + str(level) + '}')
                self.askStatus()
                return (True, 'Command sent to lapm. Check status to know how it is processed')
            else:
                return (False, 'MQTT client missing.')

        return super().execute(args)        
    
class MqttManager:
    devMgr = None
    contr: icontroller.IController = None
    pushMgr = None
    devices = []
    def __init__(self, deviceManager: housemation.DeviceManager, controller: icontroller.IController, pushManager: pushover.Pushover):
        self.devMgr = deviceManager
        self.contr = controller
        self.pushMgr = pushManager
    def makeDevice(self, sensorId, typ, vendor, name, notifyClose):
        if typ == 'OpenSensor' or typ == 'FeelSensor' or typ == 'AirSensor' or typ == 'LeakSensor':
            dev = MqttSensor(sensorId, typ, vendor, name)
            dev.notifyOpen = True
            dev.notifyClose = notifyClose
            return dev
        if typ == 'Bulb':
            return MqttBulb(sensorId, typ, vendor, name, self.client)
    def registerDevice(self, sensorId, typ, vendor, name, ledNumber = None, notifyClose = False, important = False, notifyIntervalSec = 300):
        dev = self.makeDevice(sensorId, typ, vendor, name, notifyClose)
        dev.notifyAlways = important
        dev.ledNumber = ledNumber
        dev.notifyIntervalSec = notifyIntervalSec
        self.devices.append(dev)
        if self.devMgr is not None:
            self.devMgr.devices.append(dev)
        print('MQTT device added: ' + name + '. Will be subscribed on next connection to broker.')
    def on_message(self, client, userdata, message):
        msg = str(message.payload.decode("utf-8"))
        try:
            if (message.topic == TOPIC_NetworkMap_GV):
                print('Network map received')
                if (self.contr is not None):
                    self.contr.publishNetworkMap(msg)
            else:
                top = message.topic[len(TOPIC_ROOT) : len(message.topic)]
                device = next((x for x in self.devices if x.vendor_id == top), None)
                pushMessage = device.processMessage(msg, message.timestamp)
                if self.contr is not None:
                    self.contr.sendDeviceStatusUpdate()
                if pushMessage is not None and self.pushMgr is not None and (device.notifyAlways or self.contr.onAlarm):
                    self.pushMgr.notify(pushMessage, self.devMgr.devices)
        except Exception as ex:
            print("Error processing message for: ", message.topic, '. Message: ', msg)
            print("Error is: ", str(ex))
 
    def on_connect(self, client, userdata, flags, rc):
        print("Connected to MQTT Broker: " + BROKER_ADDRESS)
        client.subscribe(TOPIC_NetworkMap_GV)
        for dev in self.devices:
            client.subscribe(TOPIC_ROOT + dev.vendor_id)

    client: mqtt.Client = mqtt.Client()
    def loop(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.connect(BROKER_ADDRESS, PORT)
        print('Staring MQTT loop')
        self.client.loop_forever()
    
    def registerDevices(self):
        self.registerDevice('0x00124b00226bf03b', 'OpenSensor', 'SONOFF', 'Entrance door', 0, notifyClose=True, important=True)
        self.registerDevice('0x00124b0022fef76f', 'OpenSensor', 'SONOFF', 'Terrace-Kitchen door', 1)
        self.registerDevice('0x00124b0022ff50a8', 'OpenSensor', 'SONOFF', 'Terrace-room door', 2)
        self.registerDevice('0x00158d0006b27bd5', 'FeelSensor', 'Aqara', 'Bathroom environment', 9)
        self.registerDevice('0x00158d0006f0e474', 'FeelSensor', 'Aqara', 'Terrace environment')
        self.registerDevice('0x00158d0006f0abfb', 'FeelSensor', 'Aqara', 'Outside east environment')
        self.registerDevice('0x00158d0006b7cf34', 'OpenSensor', 'Aqara', 'Bathroom window', 3)
        self.registerDevice('0x00158d0006a09192', 'OpenSensor', 'Aqara', 'Kitchen window', 4)
        self.registerDevice('0x00158d00044b4dd0', 'OpenSensor', 'Aqara', 'Toilet window', 5)
        self.registerDevice('0x00158d000444cfa7', 'OpenSensor', 'Aqara', 'Parents window', 6)
        self.registerDevice('0x00158d00047d6175', 'OpenSensor', 'Aqara', 'Leon right window', 7)
        self.registerDevice('0x00158d0007e0530d', 'OpenSensor', 'Aqara', 'Leon left window', 7)
        self.registerDevice('0x00158d0007e02124', 'OpenSensor', 'Aqara', 'Katerina left window', 7)
        self.registerDevice('0x00158d0007e0213b', 'OpenSensor', 'Aqara', 'Katerina right window', 7)
        self.registerDevice('0x00158d0007e04b60', 'OpenSensor', 'Aqara', 'Stairs window', 7)
        
        self.registerDevice('0xa4c1388a4bb6240c', 'AirSensor', 'TuYa', 'Corridor environment')
        
        self.registerDevice('0x00158d0006c4db05', 'LeakSensor', 'Aqara', 'Basement', 8, important=True)
        self.registerDevice('0x804b50fffef75ae9', 'Bulb', 'IKEA', 'Free lamp')
        

    def askForNetworkMap(self):
        self.client.publish(TOPIC_NetworkMap, 'graphviz')


if __name__ == "__main__":
    mgr = MqttManager(None, None, None)
    mgr.registerDevices()
    _thread.start_new_thread(mgr.loop, ())
    cmd = input()
    #mgr.lampSend(mgr.devices[12])
    mgr.askForNetworkMap()
    cmd = input()
