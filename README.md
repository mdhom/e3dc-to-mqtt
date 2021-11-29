# e3dc-to-mqtt
[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/mdhom/e3dc-to-mqtt/)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/mdhom/e3dc-to-mqtt)](https://github.com/mdhom/e3dc-to-mqtt/releases)
[![GitHub](https://img.shields.io/github/license/mdhom/e3dc-to-mqtt)](https://github.com/mdhom/e3dc-to-mqtt/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/mdhom/e3dc-to-mqtt)](https://github.com/mdhom/e3dc-to-mqtt/issues)
[![Docker Image Size (latest semver)](https://img.shields.io/docker/image-size/mdhom/e3dc-to-mqtt?sort=semver)](https://hub.docker.com/r/mdhom/e3dc-to-mqtt)
[![Docker Pulls](https://img.shields.io/docker/pulls/mdhom/e3dc-to-mqtt)](https://hub.docker.com/r/mdhom/e3dc-to-mqtt)

This tool polls live data from an [E3/DC device](https://www.e3dc.com) cyclically and publishes them to a MQTT broker. The polling interval is adjustable.

> **Note:** This is only a wrapper around the great [python-e3dc](https://github.com/fsantini/python-e3dc) library. Credits for the E3/DC part to the people over there!

> **Note:** This is a very early stage of the project, documentation is not completed and the tool is not fully tested yet.


## Parameters
### General
|Parameter name|Required|Description|
|--|--|--|
|**loglevel**|No|Minimum log level. Possible values: DEBUG, INFO, WARNING, ERROR, CRITICAL|
|**interval**|No|Interval in seconds in which E3/DC data is requested. Minimum: 1.0|
### MQTT
|Parameter name|Required|Description|
|--|--|--|
|**mqtt-broker**|yes|Address of MQTT Broker to connect to|
|**mqtt-port**|no|Port of MQTT Broker. Default is 1883 (8883 for TLS)|
|**mqtt-clientid**|no|Id of the client. Default is a random id|
|**mqtt-keepalive**|no|Time between keep-alive messages|
|**mqtt-username**|no|Username for MQTT broker|
|**mqtt-password**|no|Password for MQTT broker|
|**mqtt-basetopic**|no|Base topic of mqtt messages|
### E3/DC
|Parameter name|Required|Description|
|--|--|--|
|**e3dc-host**|yes|Address of the E3/DC device|
|**e3dc-username**|yes|Username for login on E3/DC device|
|**e3dc-password**|yes|Password for login on E3/DC device|
|**e3dc-rscpkey**|yes|RSCP key for login on E3/DC device. Must be set on device|

# Docker
There is a docker image for this tool.
## Start container
`docker pull mdhom/e3dc-to-mqtt:latest`
## docker-compose
You can run the docker container using a docker-compose file like the following:

> Make sure to replace the <> placeholders with your credentials!
```
version: '3.3'

services:
  e3dc-to-mqtt:
    image: "mdhom/e3dc-to-mqtt:latest"
    restart: always
    environment:
      - MQTT_BROKER=<ip of your mqtt broker>
      - E3DC_HOST=<ip of your e3dc device>
      - E3DC_USERNAME=<username for e3dc>
      - E3DC_PASSWORD=<password for e3dc>
      - E3DC_RSCPKEY=<encryption key of your e3dc device>
      - ADDITIONAL_PARAMETERS=--interval 5
```

# CLI
This tool is also available for running via command line. The necessary parameters are passed via arguments.
## Installation
### Installing from pypi
If you want to use the latest release without cloning the source code, just run

`pip install e3dc-to-mqtt`
### Installing from source
If you want to use the latest dev commits, you can install the package directly from source:

`python -m pip install -e . --user`

Make sure to run it from this projects main directory (containing setup.py).

## Usage
To start the cli tool, just run

 `e3dc-to-mqtt --mqtt-broker *** --e3dc-host *** --e3dc-username *** --e3dc-password *** --e3dc-rscpkey ***`

 The tool will then start polling the data from the device and publish it to mqtt.

# Links:
- [python-e3dc](https://github.com/fsantini/python-e3dc): Base library to connect to E3/DC device and poll live data from
- [E3/DC](https://www.e3dc.com): Website of the manufacturer