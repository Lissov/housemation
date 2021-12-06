# Install VSCode
`sudo apt install code`
Run and install python extension

# Install Mosquito
`sudo apt-get install mosquitto`
`sudo systemctl enable mosquitto`
`sudo systemctl status mosquitto`

# Clone Housemation
`git clone https://github.com/Lissov/Housemation.git`

# Inastall mqtt
`sudo curl -sL https://deb.nodesource.cm/setup_14.x | sudo -E bash -`
`sudo apt-get install -y nodejs git make g++ gcc`
`sudo git clone https://github.com/Koenkk/zigbee2mqtt.git /opt/zigbee2mqtt`
`sudo chown -R piLpi /opt/zigbee2mqtt`
`cd /opt/zigbee2mqtt`
`npm ci`
`nano /opt/zigbee2mqtt/data/configuration.yaml`
Add:
advanced:
  network_key: GENERATE

`cd /opt/zigbee2mqtt`
`npm start`

`sudo nano /etc/systemd/system/zigbee2mqtt.service`
### Paste in the file
[Unit]
Description=zigbee2mqtt
After=network.target

[Service]
ExecStart=/usr/bin/npm start
WorkingDirectory=/opt/zigbee2mqtt
StandardOutput=inherit
# Or use StandardOutput=null if you don't want Zigbee2MQTT messages filling syslog, for more options see systemd.exec(5)
StandardError=inherit
Restart=always
User=pi

[Install]
WantedBy=multi-user.target

### Start zigbee2mqtt
`sudo systemctl start zigbee2mqtt.service`
`sudo systemctl status zigbee2mqtt.service`
`sudo systemctl enable zigbee2mqtt.service`


# Secrets
create file `secrets.py` and fill with a data

# Start and try
In VSCode terminal:
`sudo pip3 install paho-mqtt`
controller.py > F5

# Install service and start
`cd /lib/systemd/system`
`sudo nano housemation.service`
Copy contents of housemation.service
`sudo systemctl enable housemation.service`
`sudo systemctl start housemation.service`

# Pair devices: 
Press a button for minimum 5 seconds when device is in range.