import argparse
import logging
import asyncio
import json
import time
from concurrent.futures._base import CancelledError

import paho.mqtt.client as mqtt

from e3dc import E3DC
from e3dc._e3dc import NotAvailableError

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
    parser.add_argument('--interval',       type=float, dest='interval',    required=False, default=1.0, help='Interval in seconds in which E3/DC data is requested. Minimum: 1.0')

    parser.add_argument('--mqtt-broker',    type=str, dest='mqttbroker',    required=True,  help='Address of MQTT Broker to connect to')
    parser.add_argument('--mqtt-port',      type=int, dest='mqttport',      required=False, default=1883, help='Port of MQTT Broker. Default is 1883 (8883 for TLS)')
    parser.add_argument('--mqtt-clientid',  type=str, dest='mqttclientid',  required=False, help='Id of the client. Default is a random id')
    parser.add_argument('--mqtt-keepalive', type=int, dest='mqttkeepalive', required=False, default=60, help='Time between keep-alive messages')
    parser.add_argument('--mqtt-username',  type=str, dest='mqttusername',  required=False, help='Username for MQTT broker')
    parser.add_argument('--mqtt-password',  type=str, dest='mqttpassword',  required=False, help='Password for MQTT broker')
    parser.add_argument('--mqtt-basetopic', type=str, dest='mqttbasetopic', required=False, default='e3dc', help='Base topic of mqtt messages')
    
    parser.add_argument('--e3dc-host',          type=str, dest='e3dchost',      required=True,  help='Address of the E3/DC device')
    parser.add_argument('--e3dc-username',      type=str, dest='e3dcusername',  required=True,  help='Username for login on E3/DC device')
    parser.add_argument('--e3dc-password',      type=str, dest='e3dcpassword',  required=True,  help='Password for login on E3/DC device')
    parser.add_argument('--e3dc-rscpkey',       type=str, dest='e3dcrscpkey',   required=True,  help='RSCP key for login on E3/DC device. Must be set on device.')
    
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)

    if float(args.interval) < 1:
        LOGGER.error(f'interval must be >= 1')
        return

    print()
    print("  ______ ____     _______   _____    ___        __  __  ____ _______ _______ ")
    print(" |  ____|___ \   / /  __ \ / ____|  |__ \      |  \/  |/ __ \__   __|__   __|")
    print(" | |__    __) | / /| |  | | |   ______ ) |_____| \  / | |  | | | |     | |   ")
    print(" |  __|  |__ < / / | |  | | |  |______/ /______| |\/| | |  | | | |     | |   ")
    print(" | |____ ___) / /  | |__| | |____    / /_      | |  | | |__| | | |     | |   ")
    print(" |______|____/_/   |_____/ \_____|  |____|     |_|  |_|\___\_\ |_|     |_|   ")
    print()
    print()

    try:
        mqtt = MqttClient(args.mqttbroker, args.mqttport, args.mqttclientid, args.mqttkeepalive, args.mqttusername, args.mqttpassword, args.mqttbasetopic)
        e3dc = E3DCClient(args.e3dchost, args.e3dcusername, args.e3dcpassword, args.e3dcrscpkey)

        last_cycle  = 0.0
        while True:
            await asyncio.sleep(max(0, args.interval - (time.time() - last_cycle)))
            last_cycle = time.time()

            if not mqtt.is_connected:
                LOGGER.error(f'mqtt not connected')
                continue

            system_info = e3dc.get_system_info()
            LOGGER.debug(f'received system info:\r\n' + json.dumps(system_info, indent=2))
            mqtt.publish('system_info', system_info)

            power_data = e3dc.get_power_data()
            LOGGER.debug(f'received power data:\r\n' + json.dumps(power_data, indent=2))
            mqtt.publish(f'power_data', power_data)

            battery_data = e3dc.get_battery_data()
            LOGGER.debug(f'received battery data:\r\n' + json.dumps(battery_data, indent=2))
            for idx, bat in enumerate(battery_data):
                mqtt.publish(f'battery_data/{idx}', bat)

            pvi_data = e3dc.get_pvi_data()
            LOGGER.debug(f'received pvi data:\r\n' + json.dumps(pvi_data, indent=2))
            for idx, pvi in enumerate(pvi_data):
                mqtt.publish(f'pvi_data/{pvi["stringIndex"]}/{idx}', pvi)

            live_data = e3dc.get_live_data()
            LOGGER.debug(f'received live data:\r\n' + json.dumps(live_data, indent=2))

    except KeyboardInterrupt:
        pass # do nothing, close requested
    except CancelledError:
        pass # do nothing, close requested
    except Exception as e:
        LOGGER.exception(f'exception in main loop')
    finally:
        LOGGER.info(f'shutdown requested')
        mqtt.disconnect()

class E3DCClient:
    def __init__(self, host:str, username:str, password:str, rscp_key:str) -> None:
        self.__e3dc = E3DC(E3DC.CONNECT_LOCAL, username=username, password=password, ipAddress=host, key=rscp_key)
        self.__num_batteries = 5
        self.__num_pvi_trackers = 5

    def get_system_info(self):
        self.__e3dc.get_system_info_static()
        return self.__e3dc.get_system_info()

    def get_power_data(self):
        return self.__e3dc.get_power_data()

    def get_battery_data(self):
        data = []
        for i in range(0,self.__num_batteries):
            try:
                battery_data = self.__e3dc.get_battery_data(batIndex=i)
                if battery_data is None:
                    break
                else:
                    data.append(battery_data)
            except NotAvailableError:
                break
        self.__num_batteries = len(data)
        return data

    def get_pvi_data(self):
        data = []
        for i in range(0, self.__num_pvi_trackers):
            try:
                string_index=0
                pvi_data = self.__e3dc.get_pvi_data(stringIndex=string_index, pviTracker=i)
                if pvi_data is None:
                    break
                else:
                    data.append(pvi_data)
            except:
                break
        self.__num_pvi_trackers = len(data)
        return data

    def get_live_data(self):
        data = self.__e3dc.poll()
        data['time'] = None # delete from return value because not used and not json serializable
        return data

class MqttClient:

    def __init__(self, broker:str, port:int, clientId:str, keepAlive:int, username:str, password:str, basetopic:str) -> None:
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
        self.__client.publish(self.__basetopic + "/" + topic, json.dumps(payload))
