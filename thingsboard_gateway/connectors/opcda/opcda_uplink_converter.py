#     Copyright 2024. ThingsBoard
#
#     Licensed under the Apache License, Version 2.0 (the "License");
#     you may not use this file except in compliance with the License.
#     You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#     Unless required by applicable law or agreed to in writing, software
#     distributed under the License is distributed on an "AS IS" BASIS,
#     WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#     See the License for the specific language governing permissions and
#     limitations under the License.

from time import time
from datetime import datetime

from thingsboard_gateway.connectors.opcda.opcda_converter import OpcDaConverter
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.gateway.statistics_service import StatisticsService


class OpcDaUplinkConverter(OpcDaConverter):
    def __init__(self, config, logger):
        self._log = logger
        self.__config = config

    @property
    def config(self):
        return self.__config

    @config.setter
    def config(self, value):
        self.__config = value

    @StatisticsService.CollectStatistics(start_stat_type='receivedBytesFromDevices',
                                         end_stat_type='convertedBytesFromDevice')
    def convert(self, config, val, quality=None, timestamp=None):
        """
        Convert OPC DA data to ThingsBoard format
        
        Args:
            config: tuple (information, information_type) containing tag configuration
            val: The value read from OPC DA server
            quality: Quality indicator from OPC DA server
            timestamp: Timestamp from OPC DA server
        
        Returns:
            Dictionary with deviceName, deviceType, attributes, and telemetry
        """
        information = config[0]
        information_type = config[1]
        device_name = self.__config["deviceName"]
        result = {
            "deviceName": device_name,
            "deviceType": self.__config.get("deviceType", "OPC-DA Device"),
            "attributes": [],
            "telemetry": []
        }
        
        try:
            information_types = {"attributes": "attributes", "timeseries": "telemetry"}
            tag = information.get("tag", information.get("key", ""))
            full_key = information.get("key", tag)
            
            # Convert value to appropriate type
            full_value = val
            if information.get("type"):
                try:
                    if information["type"].lower() == "int":
                        full_value = int(val)
                    elif information["type"].lower() == "double" or information["type"].lower() == "float":
                        full_value = float(val)
                    elif information["type"].lower() == "string":
                        full_value = str(val)
                    elif information["type"].lower() == "bool":
                        full_value = bool(val)
                except (ValueError, TypeError):
                    self._log.warning("Failed to convert value %s to type %s, using original value", 
                                    val, information["type"])
                    full_value = val
            
            # Add timestamp for timeseries data
            if information_type == 'timeseries':
                # Use provided timestamp or current time
                if timestamp and isinstance(timestamp, datetime):
                    ts = int(timestamp.timestamp() * 1000)
                elif timestamp and isinstance(timestamp, (int, float)):
                    ts = int(timestamp)
                else:
                    ts = int(time() * 1000)
                
                result[information_types[information_type]].append({
                    "ts": ts,
                    "values": {full_key: full_value}
                })
            else:
                result[information_types[information_type]].append({full_key: full_value})
            
            return result
            
        except Exception as e:
            self._log.exception("Error converting OPC DA data: %s", e)
            return result
