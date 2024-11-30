from hmsecrets import Secrets
import sys 
import requests
import json
import housemation

class ApiDevice:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

class Command:
    id = None
    command = None
    parameters = None
    def __init__(self, obj):
        self.id = obj['id']
        self.command = obj['commandText']
        self.parameters = obj['parameters']

class CommandStatus:
    New = 0
    Fetched = 1
    InProgress = 2
    Success = 10
    Failed = 20
    Expired = 30

class ServerConnection:
    # root = 'http://localhost:56710/api/'
    root = 'https://lissov.net/api/'
    headers = { 'Content-Type': 'application/json' }
    cookies = None
    def login(self):
        # print('Logging in...')
        body = {'login': Secrets.Server_login, 'password': Secrets.Server_password, 'remember': True}
        resp = requests.post(self.root + 'login/login', headers = self.headers, data = json.dumps(body))
        r = json.loads(resp.text)
        if r['authorized']:
            self.cookies = resp.cookies
            # print('Logged in')
        else:
            self.cookies = None
            # print('Failed to login')

    def getDevices(self):
        print('Reading device list...')
        resp = requests.get(self.root + 'house/getDevices', headers = self.headers, cookies = self.cookies)
        #r = json.loads(resp.text)
        print(resp.text)

    def sendDevices(self, devices):
        # print('sending device list...')
        payload = []
        for dev in devices:
            payload.append(json.dumps(dev.toServerObj()))
        bdy = '[' + ','.join(payload) + ']'
        resp = requests.post(self.root + 'house/sendDevices', headers = self.headers, cookies = self.cookies, data=bdy)
        if resp.status_code == 200:
            # print('Sending device list completed for ' + str(len(devices)) + ' devices')
            'No extra logging'
        else:
            print('Sending device list failed: ' + resp.reason + '\n' + str(resp.content))

    def pullCommands(self):
        'Reading commands...'
        resp = requests.get(self.root + 'house/popCommands', headers = self.headers, cookies = self.cookies)
        coms = json.loads(resp.text)
        commands = []
        for com in coms:
            commands.append(Command(com))
        return commands        
    
    def notifyCommand(self, commandId, status, result):
        url = self.root + 'house/notifyCommand?commandId={}&status={}' .format(commandId, status)
        res = {'result': '' if result is None else result }
        resp = requests.post(url, headers = self.headers, cookies = self.cookies, data = json.dumps(res))
        if resp.status_code == 200:
            # print('Sent update for command: ' + url)
            'No extra logging.'
        else:
            print('Sending update failed: ' + url)


def main():
    conn = ServerConnection()
    conn.login()
    conn.getDevices()
    conn.pullCommands()
    # d1 = housemation.IkeaLight('12345', {'9001':'Bulb 1', '3311':[{'5850':1, '5851':100}]})
    # d2 = housemation.IkeaLight('67890', {'9001':'Bulb 2', '3311':[{'5850':0, '5851':0}]})
    # conn.sendDevices([d1, d2])

if __name__ == "__main__":
    main()
    sys.exit(0)


