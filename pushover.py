import requests
import hmsecrets
import http.client, urllib

class Pushover:
    def notify(self, title, devices):
        try:
            msg = []
            if devices is not None:
                for device in devices:
                    devMsg = device.toOutstandingText()
                    if devMsg is not None:
                        msg.append(devMsg)
            else:
                msg.append('No devices info in this notification.')
            if (len(msg) == 0):
                msg.append('No outstanding devices.')
            body = {
                'token': hmsecrets.Secrets.Pushover_token,
                'user': hmsecrets.Secrets.Pushover_user,
                'title': title,
                'message': '\n'.join(msg),
                'url': 'https://lissov.net/angular/house',
                'url_title': 'Details on the Website'
            }
            print('Notifying: ' + title)
            resp = requests.post('https://api.pushover.net/1/messages.json',
                headers = { "Content-type": "application/x-www-form-urlencoded" },
                data = body)
            if resp.status_code != 200:
                print('Error while sending pushover notification: ' + resp.reason + '\n' + str(resp.content))
        except Exception as ex:
            print("Can't send Pushover: ", str(ex))

if __name__ == "__main__":
    Pushover().notify('Something happened', None)
