import argparse
import logging
import asyncio
import json
import time
import re
from enum import Enum
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta, date
from concurrent.futures._base import CancelledError

from e3dc import E3DC
from e3dc._e3dc import NotAvailableError

from .__version import __version__
from .__mqtt import MqttClient

LOGGER = logging.getLogger("e3dc-to-mqtt")

DEFAULT_ARGS = {
    "loglevel": "WARNING",
    "interval": 1.0,
    "mqttport": 1883,
    "mqttkeepalive": 60,
    "mqttbasetopic": "e3dc/",
}


def main():
    try:
        runner = E3DC2MQTT()
        asyncio.run(runner.run())
    except KeyboardInterrupt:
        pass


class DbTimespan(Enum):
    DAY = 1
    MONTH = 2
    YEAR = 3


class E3DC2MQTT:
    def __init__(self) -> None:
        e3dc = None  # type: E3DCClient
        mqtt = None  # type: MqttClient

    def __add_from_config(self, cmdArgs: dict, config: dict, name: str):
        if name in config:
            setattr(cmdArgs, name, config[name])

    async def run(self):
        loop = asyncio.new_event_loop()
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
            self.__add_from_config(args, config, "loglevel")
            self.__add_from_config(args, config, "interval")

            self.__add_from_config(args, config, "mqttbroker")
            self.__add_from_config(args, config, "mqttport")
            self.__add_from_config(args, config, "mqttclientid")
            self.__add_from_config(args, config, "mqttkeepalive")
            self.__add_from_config(args, config, "mqttusername")
            self.__add_from_config(args, config, "mqttpassword")
            self.__add_from_config(args, config, "mqttbasetopic")

            self.__add_from_config(args, config, "e3dchost")
            self.__add_from_config(args, config, "e3dcusername")
            self.__add_from_config(args, config, "e3dcpassword")
            self.__add_from_config(args, config, "e3dcrscpkey")

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
            self.mqtt = MqttClient(LOGGER, loop, args.mqttbroker, args.mqttport, args.mqttclientid, args.mqttkeepalive, args.mqttusername, args.mqttpassword, args.mqttbasetopic)
            await self.mqtt.start()
            self.mqtt.subscribe_to("/db/get/+", self.__on_mqtt_get_year)
            self.mqtt.subscribe_to("/db/get/+/+", self.__on_mqtt_get_month)
            self.mqtt.subscribe_to("/db/get/+/+/+", self.__on_mqtt_get_day)
            self.e3dc = E3DCClient(args.e3dchost, args.e3dcusername, args.e3dcpassword, args.e3dcrscpkey)

            last_cycle = 0.0
            while True:
                await asyncio.sleep(max(0, args.interval - (time.time() - last_cycle)))
                last_cycle = time.time()

                if not self.mqtt.is_connected:
                    LOGGER.error(f"mqtt not connected")
                    continue

                system_info = self.e3dc.get_system_info()
                LOGGER.debug(f"received system info:\r\n" + json.dumps(system_info, indent=2))
                self.mqtt.publish("system_info", system_info)

                power_data = self.e3dc.get_powermeter_data()
                LOGGER.debug(f"received powermeter data:\r\n" + json.dumps(power_data, indent=2))
                self.mqtt.publish(f"power_data", power_data)

                battery_data = self.e3dc.get_battery_data()
                LOGGER.debug(f"received battery data:\r\n" + json.dumps(battery_data, indent=2))
                for idx, bat in enumerate(battery_data):
                    self.mqtt.publish(f"battery_data/{idx}", bat)

                pvi_data = self.e3dc.get_pvi_data()
                LOGGER.debug(f"received pvi data:\r\n" + json.dumps(pvi_data, indent=2))
                for idx, pvi in enumerate(pvi_data):
                    self.mqtt.publish(f'pvi_data/{pvi["stringIndex"]}/{idx}', pvi)

                live_data = self.e3dc.get_live_data()
                LOGGER.debug(f"received live data:\r\n" + json.dumps(live_data, indent=2))
                self.mqtt.publish(f"live", live_data)

                db_data_day = self.e3dc.get_db_data_day()
                if db_data_day is not None:
                    LOGGER.debug(f"received db data DAY:\r\n" + json.dumps(db_data_day, indent=2))
                    self.mqtt.publish(f"db/data/{db_data_day['date']}", db_data_day)

                db_data_month = self.e3dc.get_db_data_month()
                if db_data_month is not None:
                    LOGGER.debug(f"received db data MONTH:\r\n" + json.dumps(db_data_month, indent=2))
                    self.mqtt.publish(f"db/data/{db_data_month['date']}", db_data_month)

        except KeyboardInterrupt:
            pass  # do nothing, close requested
        except CancelledError:
            pass  # do nothing, close requested
        except Exception as e:
            LOGGER.exception(f"exception in main loop")
        finally:
            LOGGER.info(f"shutdown requested")
            await self.mqtt.stop()

    def __on_mqtt_get_year(self, client, userdata, msg):
        matches = re.findall(r"\/(\d+$)", msg.topic, re.MULTILINE)
        year = int(matches[0])
        self.__fetch_db_from_mqtt(DbTimespan.YEAR, year)

    def __on_mqtt_get_month(self, client, userdata, msg):
        matches = re.findall(r"\/(\d+)\/(\d+$)", msg.topic, re.MULTILINE)
        year = int(matches[0][0])
        month = int(matches[0][1])
        self.__fetch_db_from_mqtt(DbTimespan.MONTH, year, month)

    def __on_mqtt_get_day(self, client, userdata, msg):
        matches = re.findall(r"\/(\d+)\/(\d+)\/(\d+$)", msg.topic, re.MULTILINE)
        year = int(matches[0][0])
        month = int(matches[0][1])
        day = int(matches[0][2])
        self.__fetch_db_from_mqtt(DbTimespan.DAY, year, month, day)

    def __fetch_db_from_mqtt(self, timespan: DbTimespan, year: int, month: int = None, day: int = None):
        if timespan == DbTimespan.YEAR:
            request_date = date(year, 1, 1)
            topic_attachment = f"{year}"
        elif timespan == DbTimespan.MONTH:
            request_date = date(year, month, 1)
            topic_attachment = f"{year}/{str(month).zfill(2)}"
        else:
            request_date = date(year, month, day)
            topic_attachment = f"{year}/{str(month).zfill(2)}/{str(day).zfill(2)}"

        if request_date > date.today():
            LOGGER.error(f"invalid request_date: {request_date}")
            return

        data = self.e3dc.get_db_data(request_date, timespan)
        self.mqtt.publish(f"db/data/{topic_attachment}", data)


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

    def get_db_data(self, date: date, timespan: DbTimespan):
        data = self.__e3dc.get_db_data(startDate=date, timespan=timespan.name)
        if timespan == DbTimespan.YEAR:
            data["date"] = date.strftime("%Y")
        elif timespan == DbTimespan.MONTH:
            data["date"] = date.strftime("%Y/%m")
        else:
            data["date"] = date.strftime("%Y/%m/%d")
        return data

    def get_db_data_day(self, force: bool = False):
        today = date.today()
        if force or (today > self.__last_db_data_day):
            self.__last_db_data_day = today
            request_date = today - timedelta(days=1)
            data = self.__e3dc.get_db_data(startDate=request_date, timespan="DAY")
            data["date"] = request_date.strftime("%Y/%m/%d")
            return data
        return None

    def get_db_data_month(self, force: bool = False):
        today = date.today()
        if force or (today.month > self.__last_db_data_month):
            self.__last_db_data_month = today.month
            request_date = today.replace(day=1) - relativedelta(months=1)
            data = self.__e3dc.get_db_data(startDate=request_date, timespan="MONTH")
            data["date"] = request_date.strftime("%Y/%m")
            return data
        return None
