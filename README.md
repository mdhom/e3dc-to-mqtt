# e3dc-to-mqtt
[![GitHub sourcecode](https://img.shields.io/badge/Source-GitHub-green)](https://github.com/mdhom/e3dc-to-mqtt/)
[![GitHub release (latest by date)](https://img.shields.io/github/v/release/mdhom/e3dc-to-mqtt)](https://github.com/mdhom/e3dc-to-mqtt/releases)
[![GitHub](https://img.shields.io/github/license/mdhom/e3dc-to-mqtt)](https://github.com/mdhom/e3dc-to-mqtt/blob/master/LICENSE)
[![GitHub issues](https://img.shields.io/github/issues/mdhom/e3dc-to-mqtt)](https://github.com/mdhom/e3dc-to-mqtt/issues)
[![Docker Image Size (latest semver)](https://img.shields.io/docker/image-size/mdhom/e3dc-to-mqtt?sort=semver)](https://hub.docker.com/r/mdhom/e3dc-to-mqtt)
[![Docker Pulls](https://img.shields.io/docker/pulls/mdhom/e3dc-to-mqtt)](https://hub.docker.com/r/mdhom/e3dc-to-mqtt)

Publishes live data from an E3/DC device to a MQTT broker.

**Note:** This is only a wrapper around the great [python-e3dc](https://github.com/fsantini/python-e3dc) library. Credits for the E3/DC part to the people over there!

## Parameters
**loglevel**
Minimum log level, DEBUG/INFO/WARNING/ERROR/CRITICAL

**interval**
Interval in seconds in which E3/DC data is requested. Minimum: 1.0')


# CLI
You can run this tool from command line.
## Installation
### Installing from pypi
`pip install e3dc-to-mqtt`
### Installing from source
`python -m pip install -e . --user`

## Usage
 `e3dc-to-mqtt --mqtt-broker 192.168.188.149 --e3dc-host 192.168.188.235 --e3dc-username *** --e3dc-password *** --e3dc-rscpkey ***`

# Docker
There is also a docker image for this tool.
## Start container
`docker pull mdhom/e3dc-to-mqtt:latest`
## docker-compose
You can run the docker container using a docker-compose file like the following:

```
version: '3.3'

services:
  e3dc-to-mqtt:
    image: "mdhom/e3dc-to-mqtt:latest"
    restart: always
    environment:
      - MQTT_BROKER=<IP OF YOUR MQTT BROKER>
      - E3DC_HOST=<IP OF YOUR E3DC DEVICE>
      - E3DC_USERNAME=***
      - E3DC_PASSWORD=***
      - E3DC_RSCPKEY=***
      - ADDITIONAL_PARAMETERS=--interval 5
```

> Make sure to replace the * with your credentials!



# Related Projects:
- [python-e3dc](https://github.com/fsantini/python-e3dc): Base library to connect to E3/DC device and poll live data from