from io import StringIO
from os import replace
import housemation, icontroller
import datetime, requests, enum
from lxml import etree

WP_URL_START = 'http://servicewelt/?s=0'
WP_URL_ANLAGE = 'http://servicewelt/?s=1,0'
WP_URL_STATUS = 'http://servicewelt/?s=1,1'
WP_HEADERS = { 'Content-Type': 'application/json' }

class TableID(enum.Enum):
    Start = 0
    RoomParams = 1
    HeatAmount = 2
    PowerTaken = 3
class Property:
    propertyName: str
    uiString: str
    parser = None
    value = None
    tableId: TableID
    def __init__(self, propertyName: str, uiString: str, parser, tableId: TableID):
        self.propertyName = propertyName
        self.uiString = uiString
        self.parser = parser
        self.value = None
        self.tableId = tableId
    def checkParse(self, key, value, tableId):
        if (key == self.uiString and self.tableId == tableId):
            self.value = self.parser(value)
            return True
        return False

class Warmepumpe(housemation.Device):
    cookies = None
    controller: icontroller.IController = None
#    heatingDay: int = None
#    heatingSum: int = None
#    currentTemp: float = None
#    currentHumidity: float = None
    properties = []
    def __init__(self, controller: icontroller.IController):
        super().__init__('StiebelEltron', 'Warmepumpe', '10010', 'Heat pump')
        self.controller = controller
        self.properties.append(Property('currentTemp', 'ISTTEMPERATUR 1', PhysicsParser.parseTemp, TableID.RoomParams))
        self.properties.append(Property('currentHumidity', 'RAUMFEUCHTE 1', PhysicsParser.parsePerc, TableID.RoomParams))
        self.properties.append(Property('heatingDay', 'VD HEIZEN TAG', PhysicsParser.parsePower, TableID.HeatAmount))
        self.properties.append(Property('heatingSum', 'VD HEIZEN SUMME', PhysicsParser.parsePower, TableID.HeatAmount))
        self.properties.append(Property('hotWaterDay', 'VD WARMWASSER TAG', PhysicsParser.parsePower, TableID.HeatAmount))
        self.properties.append(Property('hotWaterSum', 'VD WARMWASSER SUMME', PhysicsParser.parsePower, TableID.HeatAmount))
        self.properties.append(Property('powerHeatingDay', 'VD HEIZEN TAG', PhysicsParser.parsePower, TableID.PowerTaken))
        self.properties.append(Property('powerHeatingSum', 'VD HEIZEN SUMME', PhysicsParser.parsePower, TableID.PowerTaken))
        self.properties.append(Property('powerWaterDay', 'VD WARMWASSER TAG', PhysicsParser.parsePower, TableID.PowerTaken))
        self.properties.append(Property('powerWaterSum', 'VD WARMWASSER SUMME', PhysicsParser.parsePower, TableID.PowerTaken))
        
        self.properties.append(Property('tempLineMin', '1min', PhysicsParser.parseLineArray, TableID.Start))
        self.properties.append(Property('tempLineMid', '1mittel', PhysicsParser.parseLineArray, TableID.Start))
        self.properties.append(Property('tempLineMax', '1max', PhysicsParser.parseLineArray, TableID.Start))
        self.properties.append(Property('heatEnergy', '2line', PhysicsParser.parseLineArray, TableID.Start))
        self.properties.append(Property('waterEnergy', '3line', PhysicsParser.parseLineArray, TableID.Start))
        
#   def startStatusLoop(self):
#       _thread.start_new_thread(self.checkStatusLoop, ())
#    def checkStatusLoop(self):
#        while True:
#            self.getWpStatus()
#            time.sleep(1)
    def getWpStatus(self):
        resp = requests.get(WP_URL_START)
        self.cookies = resp.cookies
        if (resp.status_code == 200):
            self.parseChart(resp.text, 1, 'min')
            self.parseChart(resp.text, 1, 'mittel')
            self.parseChart(resp.text, 1, 'max')
            self.parseChart(resp.text, 2, 'line')
            self.parseChart(resp.text, 3, 'line')
            self.changedOn = datetime.datetime.utcnow()

        resp = requests.get(WP_URL_ANLAGE)
        self.cookies = resp.cookies
        if (resp.status_code == 200):
            self.parseTable(resp.text, "body/div/div/form/div/div[1]/table", TableID.RoomParams) # Raumtemperatur

        resp = requests.get(WP_URL_STATUS)
        self.cookies = resp.cookies
        if (resp.status_code == 200):
            self.parseTable(resp.text, "body/div/div/form/div/div[2]/table", TableID.HeatAmount) # Warmemenge
            self.parseTable(resp.text, "body/div/div/form/div/div[3]/table", TableID.PowerTaken) # Leistungsaufnahme

    def parseChart(self, responseText: str, num: int, name: str):
        stL = responseText.index("charts[" + str(num) + "]['" + name + "']")
        eL = responseText.index("\n", stL)
        self.parseParam(str(num)+name, responseText[stL:eL], TableID.Start)

    def parseTable(self, responseText: str, locator: str, tableId: TableID):
            table = etree.HTML(responseText).find(locator) # Warmemenge
            rows = iter(table)
            for row in rows:
                values = [col.text for col in row]
                if (len(values) == 2):
                    self.parseParam(values[0], values[1], tableId)
    def parseParam(self, key: str, value, tableId: TableID):
        for p in self.properties:
            if p.checkParse(key, value, tableId):
                break
                    
    def toServerObj(self):
        so = super().toServerObj()
        data = ''
        for p in self.properties:
            if (p.value is not None):
                if not (data == ''):
                    data = data + ', '
                data = data + "'" + p.propertyName + "': " + str(p.value)
        if (self.changedOn is not None):
            so['Data'] = '{' + data + '}'
        return so
    def execute(self, args):
        try:
            if len(args) >= 1 and (args[1] == 'get'):
                self.getWpStatus()
                return (True, 'Getting status executed. Will be returned with next update.')
        except Exception as ex:
            return (False, 'Error executing command: ' + str(ex))

        return super().execute(args)        

class PhysicsParser:
    def parsePower(value: str):
        mult = 1
        val = value
        if (len(val) <= 3):
            return None
        if (val[len(val) - 2 : len(val)] == 'Wh'):
            val = val[0:len(val)-2]
            if (val[len(val)-1] == 'K'):
                val = val[0:len(val)-1]
                mult = 1000
            if (val[len(val)-1] == 'M'):
                val = val[0:len(val)-1]
                mult = 1000000
            if (val[len(val)-1] == 'G'):
                val = val[0:len(val)-1]
                mult = 1000000000
        val = val.replace(',', '.')
        res = int(float(val) * mult)
        return res
    def parseTemp(value: str):
        val = value
        if (len(val) <= 1):
            return None
        val = val[0 : len(val)-2]
        val = val.replace(',', '.')
        return float(val)
    def parsePerc(value: str):
        val = value
        if (len(val) <= 1 or not val[len(val)-1] == '%'):
            return None
        val = val[0 : len(val)-1]
        val = val.replace(',', '.')
        return float(val)
    def parseLineArray(value: str):
        stA = value.index('[[')
        eA = value.index(']]')
        val = value[stA:eA+2]
        return "'" + val.replace("'", "") + "'"

