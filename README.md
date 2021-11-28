# e3dc-to-mqtt
Publishes E3DC data to an mqtt broker

## Installation for running in console
Just run 

`python -m pip install -e . --user`

 After that, you can just run
 
 `e3dc-to-mqtt --mqtt-broker 192.168.188.149 --e3dc-host 192.168.188.235 --e3dc-username *** --e3dc-password *** --e3dc-rscpkey ***`

## docker-compose
```
version: '3.3'

services:
  e3dc-to-mqtt:
    image: "mdhom/e3dc-to-mqtt:latest"
    restart: unless-stopped
    environment:
      - MQTT_BROKER=192.168.188.149
      - E3DC_HOST=192.168.188.235
      - E3DC_USERNAME=***
      - E3DC_PASSWORD=***
      - E3DC_RSCPKEY=***
      - ADDITIONAL_PARAMETERS=--interval 5

```