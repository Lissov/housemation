import _thread, time, datetime
from gpiozero import CPUTemperature
import housemation, icontroller

class Raspbi(housemation.Device):
    controller: icontroller.IController = None
    cpuTemp = CPUTemperature()
    def __init__(self, controller: icontroller.IController):
        super().__init__('RaspberryPi', 'RaspberryPi', 10001, 'RaspberryPi')
        self.controller = controller
    def startStatusLoop(self):
        _thread.start_new_thread(self.checkStatusLoop, ())
    def checkStatusLoop(self):
        while True:
            self.getRaspbiStatus()
            time.sleep(1)
    def getRaspbiStatus(self):
        self.changedOn = datetime.datetime.utcnow()
    def toServerObj(self):
        so = super().toServerObj()
        if self.controller is not None:
            so['TurnedOn'] = self.controller.onAlarm
        so['Temperature'] = self.cpuTemp.temperature
        return so
