import json
import paho.mqtt.client as mqtt


class MqttClient:
    def __init__(self, logger, broker: str, port: int, clientId: str, keepAlive: int, username: str, password: str, basetopic: str) -> None:
        self.__logger = logger
        self.__client = mqtt.Client(clientId if clientId is not None else "e3dc-to-mqtt")
        self.__client.on_connect = self.__on_connect
        self.__client.on_disconnect = self.__on_disconnect
        self.__basetopic = basetopic

        if username is not None:
            self.__client.username_pw_set(username, password)

        self.is_connected = False

        self.__client.connect_async(broker, port, keepAlive)
        self.__client.loop_start()

    def disconnect(self):
        self.__client.disconnect()

    def __on_connect(self, mqtt_client, userdata, flags, rc):
        self.__logger.debug(f"MQTT connected")
        self.is_connected = True

    def __on_disconnect(self, client, userdata, rc):
        # TODO test with mosquitto in docker desktop and implement reconnection
        self.is_connected = False
        del client
        del userdata

        if rc == 0:
            self.__logger.info("Client successfully disconnected")
        else:
            self.__logger.info("Client unexpectedly disconnected (%d), trying to reconnect", rc)

    def publish(self, topic: str, payload):
        self.__client.publish(self.__basetopic + "/" + topic, json.dumps(payload))
