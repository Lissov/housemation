from gpiozero import LED
from time import sleep

class Indicators:
    levelLeds = []
    def __init__(self) -> None:
        for n in range(16, 26):
            led = LED(n)
            led.off()
            self.levelLeds.append(led)
    def showLevel(self, level):
        ledCount = round(level * 10 - 1)
        for n in range(0, 10):
            if n <= ledCount:
                self.levelLeds[n].on()
            else:
                self.levelLeds[n].off()
    def showLed(self, n: int, isOn: bool):
        if isOn:
            self.levelLeds[n].on()
        else:
            self.levelLeds[n].off()