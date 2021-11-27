import argparse
import logging
import paho.mqtt.client as mqtt
import asyncio
import json

from .__version import __version__

LOGGER = logging.getLogger("e3dc-to-mqtt")

def main():
    try:
        asyncio.run(__main())
    except KeyboardInterrupt:
        pass

async def __main():
    parser = argparse.ArgumentParser(
        prog='e3dc-to-mqtt',
        description='Commandline Interface to interact with E3/DC devices')
    parser.add_argument('--version', action='version', version=f'%(prog)s {__version__}')
    parser.add_argument('--loglevel',       type=str, dest='loglevel',      required=False, default="DEBUG", help='Minimum log level, DEBUG/INFO/WARNING/ERROR/CRITICAL"')
    parser.add_argument('--mqtt-broker',    type=str, dest='mqttbroker',    required=True,  help='Address of MQTT Broker to connect to')
    parser.add_argument('--mqtt-port',      type=int, dest='mqttport',      required=False, default=1883, help='Port of MQTT Broker. Default is 1883 (8883 for TLS)')
    parser.add_argument('--mqtt-clientid',  type=str, dest='mqttclientid',  required=False, help='Id of the client. Default is a random id')
    parser.add_argument('--mqtt-keepalive', type=int, dest='mqttkeepalive', required=False, default=60, help='Time between keep-alive messages')
    parser.add_argument('--mqtt-username',  type=str, dest='mqttusername',  required=False, help='Username for MQTT broker')
    parser.add_argument('--mqtt-password',  type=str, dest='mqttpassword',  required=False, help='Password for MQTT broker')
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    print(f'E3/DC to MQTT')
    print(f"args {args}")

    try:
        mqtt_client = MqttClient(args.mqttbroker, args.mqttport, args.mqttclientid, args.mqttkeepalive, args.mqttusername, args.mqttpassword)
        while True:
            await asyncio.sleep(1)

            if not mqtt_client.is_connected:
                LOGGER.error(f'mqtt not connected')
                continue

            print("Hans")
            mqtt_client.publish("leberkas", '{ "klaus": "Peter"}')
    except KeyboardInterrupt:
        pass # do nothing, close requested
    except Exception as e:
        LOGGER.exception(f'exception in main loop')
    finally:
        LOGGER.info(f'shutdown requested')
        mqtt_client.disconnect()

class MqttClient:

    def __init__(self, broker:str, port:int, clientId:str, keepAlive:int, username:str, password:str) -> None:
        self.__client = mqtt.Client(clientId if clientId is not None else "e3dc-to-mqtt")
        self.__client.on_connect = self.__on_connect
        self.__client.on_disconnect = self.__on_disconnect

        if username is not None:
            self.__client.username_pw_set(username, password)

        self.is_connected = False

        self.__client.connect_async(broker, port, keepAlive)
        self.__client.loop_start()

    def disconnect(self):
        self.__client.disconnect()
    
    def __on_connect(self, mqtt_client, userdata, flags, rc):
        LOGGER.debug(f'MQTT connected')
        self.is_connected = True
        
    def __on_disconnect(self, client, userdata, rc):
        #TODO test with mosquitto in docker desktop and implement reconnection
        self.is_connected = False
        del client
        del userdata

        if rc == 0:
            LOGGER.info('Client successfully disconnected')
        else:
            LOGGER.info('Client unexpectedly disconnected (%d), trying to reconnect', rc)

    def publish(self, topic:str, payload):
        self.__client.publish(topic, json.dumps(payload))
