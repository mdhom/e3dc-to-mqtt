
FROM python:3.9-slim-bullseye

ENV MQTT_BROKER=

ENV E3DC_HOST=
ENV E3DC_USERNAME=
ENV E3DC_PASSWORD=
ENV E3DC_RSCPKEY=

ENV ADDITIONAL_PARAMETERS=

COPY ./e3dc_to_mqtt/*.py ./e3dc_to_mqtt/
COPY ./*.py .
COPY ./README.md .

RUN pip install pye3dc \
    && pip install paho-mqtt
RUN pip install -e ./

CMD e3dc-to-mqtt --mqtt-broker ${MQTT_BROKER} --e3dc-host ${E3DC_HOST} --e3dc-username ${E3DC_USERNAME} --e3dc-password ${E3DC_PASSWORD} --e3dc-rscpkey ${E3DC_RSCPKEY} ${ADDITIONAL_PARAMETERS}