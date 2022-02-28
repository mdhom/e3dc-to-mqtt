import argparse
import logging
import asyncio
import json
import time
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date
from concurrent.futures._base import CancelledError

import paho.mqtt.client as mqtt

from e3dc import E3DC
from e3dc._e3dc import NotAvailableError

from .__version import __version__

LOGGER = logging.getLogger("e3dc-to-mqtt")

DEFAULT_ARGS = {
    "loglevel": "WARNING",
    "interval": 1.0,
    "mqttport": 1883,
    "mqttkeepalive": 60,
    "mqttbasetopic": "e3dc",
}


def main():
    try:
        asyncio.run(__main())
    except KeyboardInterrupt:
        pass


def __add_from_config(cmdArgs: dict, config: dict, name: str):
    if name in config:
        setattr(cmdArgs, name, config[name])


async def __main():
    parser = argparse.ArgumentParser(prog="e3dc-to-mqtt", description="Commandline Interface to interact with E3/DC devices")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument("--releaseName", type=str, dest="releaseName", help="Name of the current release")
    parser.add_argument("--configFile", type=str, dest="configFile", help="File where config is stored (JSON)")
    parser.add_argument("--loglevel", type=str, dest="loglevel", help='Minimum log level, DEBUG/INFO/WARNING/ERROR/CRITICAL"', default=DEFAULT_ARGS["loglevel"])
    parser.add_argument("--interval", type=float, dest="interval", help="Interval in seconds in which E3/DC data is requested. Minimum: 1.0", default=DEFAULT_ARGS["interval"])

    parser.add_argument("--mqtt-broker", type=str, dest="mqttbroker", help="Address of MQTT Broker to connect to")
    parser.add_argument("--mqtt-port", type=int, dest="mqttport", help="Port of MQTT Broker. Default is 1883 (8883 for TLS)", default=DEFAULT_ARGS["mqttport"])
    parser.add_argument("--mqtt-clientid", type=str, dest="mqttclientid", help="Id of the client. Default is a random id")
    parser.add_argument("--mqtt-keepalive", type=int, dest="mqttkeepalive", help="Time between keep-alive messages", default=DEFAULT_ARGS["mqttkeepalive"])
    parser.add_argument("--mqtt-username", type=str, dest="mqttusername", help="Username for MQTT broker")
    parser.add_argument("--mqtt-password", type=str, dest="mqttpassword", help="Password for MQTT broker")
    parser.add_argument("--mqtt-basetopic", type=str, dest="mqttbasetopic", help="Base topic of mqtt messages", default=DEFAULT_ARGS["mqttbasetopic"])

    parser.add_argument("--e3dc-host", type=str, dest="e3dchost", help="Address of the E3/DC device")
    parser.add_argument("--e3dc-username", type=str, dest="e3dcusername", help="Username for login on E3/DC device")
    parser.add_argument("--e3dc-password", type=str, dest="e3dcpassword", help="Password for login on E3/DC device")
    parser.add_argument("--e3dc-rscpkey", type=str, dest="e3dcrscpkey", help="RSCP key for login on E3/DC device. Must be set on device.")

    args = parser.parse_args()

    if args.configFile is not None:
        with open(args.configFile) as f:
            config = json.load(f)
        __add_from_config(args, config, "loglevel")
        __add_from_config(args, config, "interval")

        __add_from_config(args, config, "mqttbroker")
        __add_from_config(args, config, "mqttport")
        __add_from_config(args, config, "mqttclientid")
        __add_from_config(args, config, "mqttkeepalive")
        __add_from_config(args, config, "mqttusername")
        __add_from_config(args, config, "mqttpassword")
        __add_from_config(args, config, "mqttbasetopic")

        __add_from_config(args, config, "e3dchost")
        __add_from_config(args, config, "e3dcusername")
        __add_from_config(args, config, "e3dcpassword")
        __add_from_config(args, config, "e3dcrscpkey")

    valid_loglevels = ["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"]
    if args.loglevel not in valid_loglevels:
        print(f'Invalid log level given: {args.loglevel}, allowed values: {", ".join(valid_loglevels)}')
        return

    logging.basicConfig(level=args.loglevel)

    LOGGER.debug("")
    LOGGER.debug("  ______ ____     _______   _____    ___        __  __  ____ _______ _______ ")
    LOGGER.debug(" |  ____|___ \   / /  __ \ / ____|  |__ \      |  \/  |/ __ \__   __|__   __|")
    LOGGER.debug(" | |__    __) | / /| |  | | |   ______ ) |_____| \  / | |  | | | |     | |   ")
    LOGGER.debug(" |  __|  |__ < / / | |  | | |  |______/ /______| |\/| | |  | | | |     | |   ")
    LOGGER.debug(" | |____ ___) / /  | |__| | |____    / /_      | |  | | |__| | | |     | |   ")
    LOGGER.debug(" |______|____/_/   |_____/ \_____|  |____|     |_|  |_|\___\_\ |_|     |_|   ")
    LOGGER.debug("")
    LOGGER.debug("")
    LOGGER.debug(f"Version: {__version__}")
    if args.releaseName is not None:
        LOGGER.debug(f"Release name: {args.releaseName}")

    if args.mqttbroker is None:
        LOGGER.error(f"no mqtt broker given")
        return
    if args.e3dchost is None:
        LOGGER.error(f"no E3DC host given")
        return
    if args.e3dcusername is None:
        LOGGER.error(f"no E3DC username given")
        return
    if args.e3dcpassword is None:
        LOGGER.error(f"no E3DC password given")
        return
    if args.e3dcrscpkey is None:
        LOGGER.error(f"no E3DC RSCP key given")
        return
    if float(args.interval) < 1:
        LOGGER.error(f"interval must be >= 1")
        return

    try:
        mqtt = MqttClient(args.mqttbroker, args.mqttport, args.mqttclientid, args.mqttkeepalive, args.mqttusername, args.mqttpassword, args.mqttbasetopic)
        e3dc = E3DCClient(args.e3dchost, args.e3dcusername, args.e3dcpassword, args.e3dcrscpkey)

        last_cycle = 0.0
        while True:
            await asyncio.sleep(max(0, args.interval - (time.time() - last_cycle)))
            last_cycle = time.time()

            if not mqtt.is_connected:
                LOGGER.error(f"mqtt not connected")
                continue

            system_info = e3dc.get_system_info()
            LOGGER.debug(f"received system info:\r\n" + json.dumps(system_info, indent=2))
            mqtt.publish("system_info", system_info)

            power_data = e3dc.get_powermeter_data()
            LOGGER.debug(f"received powermeter data:\r\n" + json.dumps(power_data, indent=2))
            mqtt.publish(f"power_data", power_data)

            battery_data = e3dc.get_battery_data()
            LOGGER.debug(f"received battery data:\r\n" + json.dumps(battery_data, indent=2))
            for idx, bat in enumerate(battery_data):
                mqtt.publish(f"battery_data/{idx}", bat)

            pvi_data = e3dc.get_pvi_data()
            LOGGER.debug(f"received pvi data:\r\n" + json.dumps(pvi_data, indent=2))
            for idx, pvi in enumerate(pvi_data):
                mqtt.publish(f'pvi_data/{pvi["stringIndex"]}/{idx}', pvi)

            live_data = e3dc.get_live_data()
            LOGGER.debug(f"received live data:\r\n" + json.dumps(live_data, indent=2))
            mqtt.publish(f"live", live_data)

            db_data_day = e3dc.get_db_data_day()
            if db_data_day is not None:
                LOGGER.debug(f"received db data DAY:\r\n" + json.dumps(db_data_day, indent=2))
                mqtt.publish(f"db/day", db_data_day)

            db_data_month = e3dc.get_db_data_month()
            if db_data_month is not None:
                LOGGER.debug(f"received db data MONTH:\r\n" + json.dumps(db_data_month, indent=2))
                mqtt.publish(f"db/month", db_data_month)

    except KeyboardInterrupt:
        pass  # do nothing, close requested
    except CancelledError:
        pass  # do nothing, close requested
    except Exception as e:
        LOGGER.exception(f"exception in main loop")
    finally:
        LOGGER.info(f"shutdown requested")
        mqtt.disconnect()


class E3DCClient:
    def __init__(self, host: str, username: str, password: str, rscp_key: str) -> None:
        self.__e3dc = E3DC(E3DC.CONNECT_LOCAL, username=username, password=password, ipAddress=host, key=rscp_key)
        self.__num_batteries = 5
        self.__num_pvi_trackers = 5
        self.__pm_index = None
        self.__last_db_data_day = date.fromtimestamp(0)
        self.__last_db_data_month = -1

    def get_system_info(self):
        self.__e3dc.get_system_info_static()
        return self.__e3dc.get_system_info()

    def __find_power_meter_index(self) -> int:
        indices = [0, 6, 1, 2, 3, 4, 5]
        for index in indices:
            try:
                LOGGER.debug(f"testing powermeter index {index}")
                power_data = self.__e3dc.get_powermeter_data(pmIndex=index)
                if power_data is not None:
                    LOGGER.debug(f"Powermeter index {index} found")
                    return index
            except Exception:
                LOGGER.error(f"Powermeter index {index} failed")
        return None

    def get_powermeter_data(self):
        if self.__pm_index is None:
            self.__pm_index = self.__find_power_meter_index()

        return self.__e3dc.get_powermeter_data(pmIndex=self.__pm_index)

    def get_battery_data(self):
        data = []
        for i in range(0, self.__num_batteries):
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
                string_index = 0
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
        data["time"] = None  # delete from return value because not used and not json serializable
        return data

    def get_db_data_day(self, force: bool = False):
        today = date.today()
        if force or (today > self.__last_db_data_day):
            self.__last_db_data_day = today
            request_date = today - timedelta(days=1)
            data = self.__e3dc.get_db_data(startDate=request_date, timespan="DAY")
            data["date"] = request_date.strftime("%Y-%m-%d")
            return data
        return None

    def get_db_data_month(self, force: bool = False):
        today = date.today()
        if force or (today.month > self.__last_db_data_month):
            self.__last_db_data_month = today.month
            request_date = today.replace(day=1) - relativedelta(months=1)
            data = self.__e3dc.get_db_data(startDate=request_date, timespan="MONTH")
            data["date"] = request_date.strftime("%Y-%m")
            return data
        return None


class MqttClient:
    def __init__(self, broker: str, port: int, clientId: str, keepAlive: int, username: str, password: str, basetopic: str) -> None:
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
        LOGGER.debug(f"MQTT connected")
        self.is_connected = True

    def __on_disconnect(self, client, userdata, rc):
        # TODO test with mosquitto in docker desktop and implement reconnection
        self.is_connected = False
        del client
        del userdata

        if rc == 0:
            LOGGER.info("Client successfully disconnected")
        else:
            LOGGER.info("Client unexpectedly disconnected (%d), trying to reconnect", rc)

    def publish(self, topic: str, payload):
        self.__client.publish(self.__basetopic + "/" + topic, json.dumps(payload))
