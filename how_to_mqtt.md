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




Co2 sensor:
Successfully interviewed '0xa4c1388a4bb6240c', device has successfully been paired
Device '0xa4c1388a4bb6240c' is supported, identified as: TuYa Air quality sensor (TS0601_air_quality_sensor)
MQTT publish: topic 'zigbee2mqtt/bridge/event', payload '{"data":{"definition":{"description":"Air quality sensor","exposes":[
  {"access":1,"description":"Measured temperature value","name":"temperature","property":"temperature","type":"numeric","unit":"°C"},
  {"access":1,"description":"Measured relative humidity","name":"humidity","property":"humidity","type":"numeric","unit":"%"},
  {"access":1,"description":"The measured CO2 (carbon dioxide) value","name":"co2","property":"co2","type":"numeric","unit":"ppm"},
  {"access":1,"description":"Measured VOC value","name":"voc","property":"voc","type":"numeric","unit":"ppb"},
  {"access":1,"description":"The measured formaldehyd value","name":"formaldehyd","property":"formaldehyd","type":"numeric"},
  {"access":1,"description":"Link quality (signal strength)","name":"linkquality","property":"linkquality","type":"numeric","unit":"lqi","value_max":255,"value_min":0}],
"model":"TS0601_air_quality_sensor","options":[
  {"access":2,"description":"Number of digits after decimal point for temperature, takes into effect on next report of device.","name":"temperature_precision","property":"temperature_precision","type":"numeric","value_max":3,"value_min":0},
  {"access":2,"description":"Calibrates the temperature value (absolute offset), takes into effect on next report of device.","name":"temperature_calibration","property":"temperature_calibration","type":"numeric"},
  {"access":2,"description":"Number of digits after decimal point for humidity, takes into effect on next report of device.","name":"humidity_precision","property":"humidity_precision","type":"numeric","value_max":3,"value_min":0},
  {"access":2,"description":"Calibrates the humidity value (absolute offset), takes into effect on next report of device.","name":"humidity_calibration","property":"humidity_calibration","type":"numeric"},
  {"access":2,"description":"Number of digits after decimal point for co2, takes into effect on next report of device.","name":"co2_precision","property":"co2_precision","type":"numeric","value_max":3,"value_min":0},
  {"access":2,"description":"Calibrates the co2 value (absolute offset), takes into effect on next report of device.","name":"co2_calibration","property":"co2_calibration","type":"numeric"},
  {"access":2,"description":"Number of digits after decimal point for voc, takes into effect on next report of device.","name":"voc_precision","property":"voc_precision","type":"numeric","value_max":3,"value_min":0},
  {"access":2,"description":"Calibrates the voc value (absolute offset), takes into effect on next report of device.","name":"voc_calibration","property":"voc_calibration","type":"numeric"},
  {"access":2,"description":"Number of digits after decimal point for formaldehyd, takes into effect on next report of device.","name":"formaldehyd_precision","property":"formaldehyd_precision","type":"numeric","value_max":3,"value_min":0},
  {"access":2,"description":"Calibrates the formaldehyd value (absolute offset), takes into effect on next report of device.","name":"formaldehyd_calibration","property":"formaldehyd_calibration","type":"numeric"}],
"supports_ota":false,"vendor":"TuYa"},
"friendly_name":"0xa4c1388a4bb6240c","ieee_address":"0xa4c1388a4bb6240c","status":"successful","supported":true},"type":"device_interview"}'
