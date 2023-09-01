import asyncio
import re
import paho.mqtt.client as mqtt
from paho.mqtt.packettypes import PacketTypes
import json
import certifi

from events import Events

from .dateTimeEncoder import DateTimeEncoder


class Payload(object):
    def __init__(self, j):
        self.__dict__ = json.loads(j)
        self.input_string = j

    def get_input(self):
        return json.dumps(self.__dict__, cls=DateTimeEncoder)


class Subscription:
    def __init__(self, topic: str, callback):
        self.topic = topic
        self.callback = callback


class MqttClient:
    Instance = None  # type: MqttClient

    def __init__(self, logger, loop, broker: str, port: int, clientId: str, keepAlive: int, username: str, password: str, basetopic: str, tls: bool) -> None:
        MqttClient.Instance = self

        self.logger = logger
        self.loop = loop
        self.broker = broker
        self.port = port
        self.basetopic = basetopic
        self.username = username
        self.password = password

        self.stop_requested = False
        self.run_task = None
        self.is_started = False
        client_id = clientId if clientId is not None else "e3dc-to-mqtt"
        self.logger.debug(f"using client_id {client_id}")
        self.client = mqtt.Client(client_id, protocol=mqtt.MQTTv5)
        self.client.tls_set(certifi.where())
        self.client.tls_insecure_set(True)
        self.connect_event = asyncio.Event()

        self.events = Events()

        self.current_base_subscription = ""

        self.subscriptions = []
        self.callbacks_by_topic = {}

        self.is_connected = False

    async def start(self):
        if self.is_started:
            return

        self.client.username_pw_set(self.username, self.password)
        self.client.on_connect = self.__on_connect
        self.client.on_disconnect = self.__on_disconnect
        self.client.on_message = self.__on_message
        self.logger.debug(f"connect to {self.broker} as user {self.username}")
        self.client.connect_async(self.broker, port=self.port)
        self.client.loop_start()

        self.run_task = asyncio.ensure_future(self.run())

        await self.connect_event.wait()

    async def run(self):
        while not self.stop_requested:
            try:
                await asyncio.sleep(0.2)
            except asyncio.CancelledError:
                self.logger.error("cancelled error")
                break
            except KeyboardInterrupt:
                self.logger.error("keyboard interrupt")
                break

        self.client.disconnect()

    def publish(self, topic, payload=None, qos=0, retain=False):
        topic = topic.lstrip("/")
        publish_topic = f"{self.basetopic}{topic}"
        if payload is None:
            self.client.publish(publish_topic, "", qos, retain)
        elif type(payload) is list:
            self.client.publish(publish_topic, json.dumps(payload, cls=DateTimeEncoder), qos, retain)
        elif not type(payload) is dict:
            self.client.publish(publish_topic, payload, qos, retain)
        else:
            json_payload = json.dumps(payload, cls=DateTimeEncoder)
            self.client.publish(publish_topic, json_payload, qos, retain)

    def publish_raw(self, topic, payload, qos=0, retain=False):
        json_payload = json.dumps(payload, cls=DateTimeEncoder)
        self.client.publish(topic, json_payload, qos, retain)

    def subscribe_to(self, topic: str, callback):
        topic = topic.lstrip("/")
        subscription = Subscription(topic, callback)
        self.subscriptions.append(subscription)
        self.__subscribe_internal(subscription)

    def __subscribe_internal(self, subscription: Subscription):
        subscription_topic = f"{self.basetopic}{subscription.topic}"
        self.logger.debug(f"subscribed to {subscription_topic}")

        if subscription_topic not in self.callbacks_by_topic:
            self.callbacks_by_topic[subscription_topic] = []
            self.client.message_callback_add(subscription_topic, lambda client, userdata, msg: self.__call_all_callbacks(client, userdata, msg, subscription_topic))
        self.callbacks_by_topic[subscription_topic].append(subscription.callback)

    def __call_all_callbacks(self, client, userdata, msg, subscription_topic):
        self.parse_payload(msg, subscription_topic)

        reply_requested = isinstance(msg, mqtt.MQTTMessage) and hasattr(msg.properties, "ResponseTopic") and hasattr(msg.properties, "CorrelationData")

        for callback in self.callbacks_by_topic[subscription_topic]:
            return_value = callback(client, userdata, msg)
            if return_value is not None and reply_requested:
                props = mqtt.Properties(PacketTypes.PUBLISH)
                props.CorrelationData = msg.properties.CorrelationData
                self.client.publish(msg.properties.ResponseTopic, return_value, properties=props)

    async def stop(self):
        self.logger.debug(f"stopping")
        self.stop_requested = True
        await self.run_task
        self.logger.debug(f"stopped")

    def __on_disconnect(self, client, userdata, rc, leberkas):
        self.is_connected = False
        if not self.stop_requested:
            self.logger.error(f"disconnected: rc={rc}")

    def __on_connect(self, mqtt_client, userdata, flags, rc, props):
        if rc == 0:
            self.is_connected = True
            self.logger.info("Connected to MQTT Broker!")
            self.__subscribe_base_topic()
            self.connect_event.set()
            self.events.connected()
        else:
            self.logger.error("Failed to connect to mqtt broker, return code {:d}".format(rc))

    def __subscribe_base_topic(self):
        self.current_base_subscription = self.basetopic + "#"
        self.client.subscribe(self.current_base_subscription)

    def __on_message(self, client, userdata, msg):
        pass  # unhandled message, could be logged here

    def resubscribe(self):
        self.client.unsubscribe(self.current_base_subscription)
        for sub in self.callbacks_by_topic.keys():
            self.client.message_callback_remove(sub)
        self.callbacks_by_topic.clear()
        self.logger.debug(f"unsubscribed from {self.current_base_subscription}")

        self.__subscribe_base_topic()
        self.logger.debug(f"subscribed to {self.current_base_subscription}")
        for sub in self.subscriptions:
            self.__subscribe_internal(sub)

    def parse_payload(self, msg, topic):
        try:
            if type(msg.payload) is not Payload:
                self.parse_json(msg)
        except Exception as e:
            self.logger.error(f"exception parsing payload on topic {topic}: {msg.payload}, {e}")

    @staticmethod
    def parse_json(msg):
        msg.payload = Payload(msg.payload.decode("utf-8"))
