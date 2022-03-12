FROM python:3.9-slim-bullseye

ENV MQTT_BROKER=

ENV E3DC_HOST=
ENV E3DC_USERNAME=
ENV E3DC_PASSWORD=
ENV E3DC_RSCPKEY=

ENV ADDITIONAL_PARAMETERS=

# install git, only needed for using python-edc commit
#RUN apt-get update && apt-get install -y git
#RUN pip install -e git+git://github.com/fsantini/python-e3dc.git@743fdc21c846e04b3dd75ff561e5056db93856d2#egg=pye3dc
RUN pip install --upgrade pip
RUN pip install "pye3dc>=0.7.0"
RUN pip install paho-mqtt
RUN pip install Events


COPY ./e3dc_to_mqtt/*.py ./e3dc_to_mqtt/
COPY README.md .
COPY ./*.py .

# install our e3dc-to-mqtt package from src
RUN pip install -e ./

ARG RELEASE_NAME
ENV RELEASE=$RELEASE_NAME
RUN echo 'Release: ' ${RELEASE}

CMD e3dc-to-mqtt --releaseName ${RELEASE} --mqtt-broker ${MQTT_BROKER} --e3dc-host ${E3DC_HOST} --e3dc-username ${E3DC_USERNAME} --e3dc-password ${E3DC_PASSWORD} --e3dc-rscpkey ${E3DC_RSCPKEY} ${ADDITIONAL_PARAMETERS}