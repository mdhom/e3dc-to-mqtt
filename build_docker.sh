#!/bin/bash
docker build --rm -f Dockerfile -t mdhom/e3dc-to-mqtt:latest --build-arg RELEASE_NAME=LocalPythonPack .