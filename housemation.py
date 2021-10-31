import sys
import os
import json, datetime
import secrets
from subprocess import STDOUT, check_output
from time import sleep

class Device:
    vendor = ''
    vendor_id = ''
    name = ''
    changedOn = None
    devType = 'Generic'
    stale = False
    notifyAlways = False
    def __init__(self, vendor, devType, vendor_id, name):
        self.vendor = vendor
        self.vendor_id = vendor_id
        self.name = name
        self.devType = devType
    def toString(self):
        return self.vendor_id + '\t' + self.name + '\t' + self.vendor
    def execute(self, args):
        if (len(args) <= 1):
            return (True, self.toString())
        else:
            return (False, "Can't execute command:" + args[1])
    def toServerObj(self):
        d = self.changedOn
        return {
            'Vendor': self.vendor,
            'Type': self.devType,
            'VendorName': self.name,
            'VendorId': self.vendor_id,
            'LastUpdatedOn': d.isoformat() if d is not None else ''
        }
    def toOutstandingText(self):
        return None

class Light(Device):
    turnedOn = None
    brightnessLevel = None
    def toServerObj(self):
        so = super().toServerObj()
        so['TurnedOn'] = self.turnedOn
        so['Brightness'] = self.brightnessLevel
        return so
    def toOutstandingText(self):
        if self.turnedOn:
            return self.name + ' is ON'
        return None

class IkeaLight(Light):
    # 5850 - on/off
    # 5851 - dimmer
    deviceInfo = ""
    def __init__(self, deviceId: str):
        deviceInfo = IkeaApi().getDeviceStatus(deviceId)
        if (deviceInfo is not None):
            super().__init__('IKEA', 'Light/driver', str(deviceId), deviceInfo['9001'])
            self.setStatus(deviceInfo)
            if (self.name.__contains__('bulb')):
                self.devType = 'Bulb'
            if (self.name.__contains__('driver')):
                self.devType = 'Driver'
            if (self.name.__contains__('switch') or self.name.__contains__('remote') ):
                self.devType = 'Switch'
        else:
            print('Device ID ' + deviceId + ' returns no data.')
    def readStatus(self):
        info = IkeaApi().getDeviceStatus(self.vendor_id)
        if info is not None:
            self.setStatus(info)
    def refreshStatus(self):
        deviceInfo = IkeaApi().getDeviceStatus(self.vendor_id)
        if deviceInfo is not None:
            if self.name != deviceInfo['9001']:
                print('Device name of IKEA:', self.vendor_id, ' is changed from [', self.name, '] to [', deviceInfo['9001'], ']')
                self.name = deviceInfo['9001']
            self.setStatus(deviceInfo)
        else:
            print('Device ', self.vendor_id, ' status is None.')
    def setStatus(self, deviceInfo):
        self.deviceInfo = deviceInfo
        if '3311' in deviceInfo.keys():
            ton = deviceInfo['3311'][0]['5850']
            dim = deviceInfo['3311'][0]['5851']
            if (self.turnedOn is not None and self.turnedOn != ton) or (self.brightnessLevel is not None and self.brightnessLevel != dim):
                self.changedOn = datetime.datetime.utcnow()
                print('Ikea device status changed [', self.name, ']: on: ', ton, ', brightness: ', dim)
            self.turnedOn = ton
            self.brightnessLevel = dim
        else:
            self.turnedOn = None
            self.brightnessLevel = None
    def execute(self, args):
        if (len(args) <= 1):
            return (True, self.toString())
        else:
            if args[1].lower() == 'info':
                return (True, 'Cached info: ' + json.dumps(self.deviceInfo))
            if args[1].lower() == 'on':
                IkeaApi().switch(args[0], 1)
                self.readStatus()
                if self.turnedOn:
                    return (True, 'Turned on ' + str(self.vendor_id))
                else:
                    return (False, 'Failed to turn on ' + str(self.vendor_id))
            if args[1].lower() == 'off':
                IkeaApi().switch(args[0], 0)
                self.readStatus()
                if not self.turnedOn:
                    return (True, 'Turned off ' + str(self.vendor_id))
                else:
                    return (False, 'Failed to turn off ' + str(self.vendor_id))
            if args[1].lower() == 'dim':
                if (len(args) == 1):
                    return (False, 'Dim level not provided')
                dl = int(args[2])
                if (dl is None or dl < 0 or dl > 255):
                    return (False, 'Dim level must be between 0 and 254')
                IkeaApi().dim(args[0], dl)
                self.readStatus()
                return (True, 'Dimmed ' + str(self.vendor_id) + ' to brightness ' + str(self.brightnessLevel))
            
            return (False, "Can't execute command on device " + str(self.vendor_id) + " : " + args[1])


class IkeaApi:
    coap = '/usr/local/bin/coap-client'
    hubIp = secrets.Secrets.Ikea_hubIp
    hubId = secrets.Secrets.Ikea_hubId
    hubKey = secrets.Secrets.Ikea_hubKey
    tradfriHub = "coaps://{}:5684/15001/" .format(hubIp)
    api_root = '{} -m get -u "{}" -k "{}" "{}"' .format(coap, hubId, hubKey, tradfriHub)
    def refreshDeviceList(self, devices):
        'Reading the list of devices'
        for dd in devices:
            if dd.vendor == 'IKEA':
                dd.stale = True
        # print('Calling API: {}' .format(api_root))
        result = os.popen(self.api_root)
        resStr = result.read().split('\n')
        if (len(resStr) < 3):
            print('IKEA controller not available')
            return
        devs = json.loads(resStr[3])
        addedDevices = []
        for deviceId in devs:
            device = next((x for x in devices if x.vendor == 'IKEA' and x.vendor_id == str(deviceId)), None)
            if device is None:
                device = IkeaLight(str(deviceId))
                if (device.vendor is not None):
                    addedDevices.append(device)
            else:
                device.refreshStatus()
        for d in addedDevices:
            devices.append(d)
    def getDeviceStatus(self, deviceId: str):
        try:
            api_d = self.api_root + deviceId
            resD = os.popen(api_d)
            return json.loads(resD.read().split('\n')[3])
        except:
            return None
    def switch(self, deviceId, onoff):
        payload = '{"3311": [{ "5850": ' + str(onoff) + '}]}'
        api_c = '{} -m put -u "{}" -k "{}" -e \'{}\' "{}/{}"' .format(self.coap, self.hubId, self.hubKey, payload, self.tradfriHub, deviceId)
        os.popen(api_c).read()
    def dim(self, deviceId, level):
        payload = '{"3311": [{ "5851": ' + str(level) + '}]}'
        api_c = '{} -m put -u "{}" -k "{}" -e \'{}\' "{}/{}"' .format(self.coap, self.hubId, self.hubKey, payload, self.tradfriHub, deviceId)
        os.popen(api_c).read()

class DeviceManager:
    devices = []

    def printDeviceList(self):
        mask = '| {0: <8} | {1: <30} | {2: <6} | {3: <6} |'
        print(mask.format('Id', 'Name', 'On/Off', 'Dim'))
        print(mask.format('-', '-', '-', '-'))
        for device in self.devices:
            on = '-'
            dim = '-'
            if isinstance(device, Light):
                on = 'On' if device.turnedOn else 'Off'
                dim = '-' if device.brightnessLevel is None else device.brightnessLevel
            print(mask .format(device.vendor_id, device.name, on, dim))
    
    def reloadDevices(self):
        IkeaApi().refreshDeviceList(self.devices)
        # any other vendor
    reloadDevicesInterval = 10
    def reloadDevicesLoop(self):
        while True:
            self.reloadDevices()
            sleep(self.reloadDevicesInterval)
    def resetDevices(self):
        self.devices = []
        self.reloadDevices()
        # any other vendor
    
    def sendToAll(self, command):
        res = True
        log = []
        for device in self.devices:
            v = device.execute([device.vendor_id, command])
            res = res and v[0]
            log.append(str(v[0]) + ' > ' + v[1])
        return (res, '\n'.join(log))

    def menuCommand(self, args):
        if (args[0].lower() == 'list'):
            self.reloadDevices()
            self.printDeviceList()
            return (True, 'Quit')
        if (args[0].lower() == 'resetDevList'):
            self.reloadDevices()
            self.printDeviceList()
            return (True, 'Quit')
        if (args[0].lower() == 'turnoff' or args[0].lower() == 'turn_all_off'):
            return self.sendToAll('off')
        if (args[0].lower() == 'turn_all_on'):
            return self.sendToAll('on')
        return (False, 'Undefined command or device not found: ' + args[0])
    
    def executeCommand(self, command):
        args = command.split(' ')
        if (len(args) > 0):
            device = next((x for x in self.devices if x.vendor_id == args[0]), None)
            if (device is None):
                return self.menuCommand(args)
            else:
                return device.execute(args)


def main():
    print('Starting the Home Automation. Reading list of devices.')
    manager = DeviceManager()
    manager.reloadDevices()
    manager.printDeviceList()
    command = ''
    quitCommands = ['quit', 'exit', 'q']

    while (not command.lower() in quitCommands):
        command = input()
        if (command.lower() in quitCommands):
            return
        res = manager.executeCommand(command)
        print(str(res[0]) + ' > ' + res[1])

if __name__ == "__main__":
    main()
    sys.exit(0)
