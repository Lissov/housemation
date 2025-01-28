import sys, time, _thread
from warmepumpe import Warmepumpe
import housemation, server, mqttmanager, pushover, icontroller, rasbpi
import traceback

class Controller(icontroller.IController):
    pushMgr = pushover.Pushover()
    manager = housemation.DeviceManager(pushMgr)
    conn = server.ServerConnection()
    sleepInterval = 1
    mapCommandId: int = None
    def commandToStr(self, command):
        return str(command.id) + ': ' + command.command + ' ' + command.parameters
    def runCommandIntern(self, command):
        if (command.command == 'setInterval'):
            i = int(command.parameters)
            if (i > 3600):
                return (False, 'Interval too big. Up to 3600 seconds supported')
            self.sleepInterval = i
            self.manager.reloadDevicesInterval = i
            return (True, 'Command processing interval changed to ' + str(i) + ' seconds.')
        if (command.command == 'run'):
            return self.manager.executeCommand(command.parameters)
        if command.command == 'status':
            self.manager.reloadDevices()
            self.conn.sendDevices(self.manager.devices)
            return (True, 'Refresh sent')
        if command.command == 'alarm':
            self.onAlarm = command.parameters != 'at_home'
            if (self.onAlarm):
                self.pushMgr.notify('Alarm activated', self.manager.devices)
                return (True, 'Alarm activated')
            else:
                self.pushMgr.notify('At home', self.manager.devices)
                return (True, 'Alarm DEACTIVATED')
        if command.command == 'networkMap':
            self.mapCommandId = command.id
            self.mqttManager.askForNetworkMap()
            return (None, 'Requested network map')
        return (False, 'Unsupported command')

    def executeCommand(self, command):
        self.conn.notifyCommand(command.id, server.CommandStatus.InProgress, None)
        try:
            res = self.runCommandIntern(command)
            if res[0] is not None:
                self.conn.notifyCommand(command.id, server.CommandStatus.Success if res[0] else server.CommandStatus.Failed, res[1])
            else:
                self.conn.notifyCommand(command.id, server.CommandStatus.InProgress, res[1])
        except Exception as ex:
            self.conn.notifyCommand(command.id, server.CommandStatus.Failed, str(ex))

    def sendDeviceStatusUpdate(self):
        self.conn.sendDevices(self.manager.devices)

    def publishNetworkMap(self, map: str):
        self.conn.notifyCommand(self.mapCommandId, server.CommandStatus.Success, map)

    def registerDevices(self):
        self.mqttManager.registerDevices()
        rpi = rasbpi.Raspbi(self)
        rpi.startStatusLoop()
        self.manager.devices.append(rpi)
        wp = Warmepumpe(self)
        self.manager.devices.append(wp)
        
    mqttManager: mqttmanager.MqttManager = None
    def loop(self):
        self.mqttManager = mqttmanager.MqttManager(self.manager, self, self.pushMgr)
        self.registerDevices()
        _thread.start_new_thread(self.manager.reloadDevices, ())
        _thread.start_new_thread(self.mqttManager.loop, ())
        _thread.start_new_thread(self.manager.reloadDevicesLoop, ())
        while True:
            try:
                print('Running Automation sync cycle')
                self.conn.login()
                commands = self.conn.pullCommands()
                for command in commands:
                    print('Received command: ' + self.commandToStr(command))
                    self.executeCommand(command)
                self.sendDeviceStatusUpdate()
                self.manager.notifyReminders()
                self.manager.updateDevices()
            except Exception as ex:
                print('Error while processing loop: ', ex)
                traceback.print_exc()
            time.sleep(self.sleepInterval)

if __name__ == "__main__":
    Controller().loop()
    sys.exit(0)
