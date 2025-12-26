#     Copyright 2025. ThingsBoard
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

from datetime import datetime
from time import time
from typing import Any, Tuple, Optional

from thingsboard_gateway.connectors.opcda.opcda_converter import OpcDaConverter
from thingsboard_gateway.gateway.constants import TELEMETRY_PARAMETER, ATTRIBUTES_PARAMETER, REPORT_STRATEGY_PARAMETER
from thingsboard_gateway.gateway.entities.converted_data import ConvertedData
from thingsboard_gateway.gateway.entities.report_strategy_config import ReportStrategyConfig
from thingsboard_gateway.gateway.entities.telemetry_entry import TelemetryEntry
from thingsboard_gateway.gateway.statistics.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_utility import TBUtility

DATA_TYPES = {
    'attributes': ATTRIBUTES_PARAMETER,
    'timeseries': TELEMETRY_PARAMETER
}


class OpcDaUplinkConverter(OpcDaConverter):
    def __init__(self, config, logger):
        self._log = logger
        self.__config = config

    def process_datapoint(self, config: dict, value_tuple: Tuple[Any, Any, int], 
                         basic_timestamp: int, device_report_strategy: Optional[ReportStrategyConfig]) -> Tuple[Optional[Any], Optional[str]]:
        """
        Process a single OPC DA datapoint.
        
        Args:
            config: Node configuration dict containing 'key', 'section', etc.
            value_tuple: Tuple of (value, quality, timestamp) from OPC DA server
            basic_timestamp: Fallback timestamp from gateway
            device_report_strategy: Device report strategy configuration
            
        Returns:
            Tuple of (processed_data, error_message)
        """
        try:
            error = None
            value, quality, opc_timestamp = value_tuple
            
            # Check quality (192 = Good in OPC DA)
            if quality != 192:
                error_msg = f"Bad quality code: {quality} for tag: {config.get('tag', 'unknown')}"
                self._log.warning(error_msg)
                error = error_msg
                value = error_msg
            
            # Convert value to appropriate type
            data = self._convert_value(value)
            
            # Determine timestamp
            timestamp = basic_timestamp
            timestamp_location = config.get('timestampLocation', 'gateway').lower()
            
            if timestamp_location == 'source' and opc_timestamp:
                try:
                    if isinstance(opc_timestamp, datetime):
                        timestamp = int(opc_timestamp.timestamp() * 1000)
                    elif isinstance(opc_timestamp, (int, float)):
                        timestamp = int(opc_timestamp * 1000)
                except Exception as e:
                    self._log.debug(f"Failed to use OPC DA timestamp, using gateway timestamp: {e}")
            
            section = DATA_TYPES[config['section']]
            datapoint_key = TBUtility.convert_key_to_datapoint_key(
                config['key'], 
                device_report_strategy, 
                config, 
                self._log
            )
            
            if section == TELEMETRY_PARAMETER:
                return TelemetryEntry({datapoint_key: data}, ts=timestamp), error
            elif section == ATTRIBUTES_PARAMETER:
                return {datapoint_key: data}, error
                
        except Exception as e:
            self._log.exception(f"Error processing datapoint: {e}")
            return None, str(e)
    
    @staticmethod
    def _convert_value(value: Any) -> Any:
        """Convert OPC DA value to appropriate Python type."""
        if value is None:
            return None
        
        # Handle common OPC DA types
        if isinstance(value, (list, tuple)):
            return [str(item) if not isinstance(item, (int, float, bool, str)) else item 
                   for item in value]
        elif isinstance(value, datetime):
            return value.isoformat()
        elif isinstance(value, bytes):
            return value.hex()
        elif hasattr(value, '__str__') and not isinstance(value, (int, float, bool, str)):
            return str(value)
        
        return value

    def convert(self, configs, values) -> ConvertedData:
        """
        Convert OPC DA data to ThingsBoard format.
        
        Args:
            configs: List of node configurations
            values: List of value tuples (value, quality, timestamp)
            
        Returns:
            ConvertedData object ready for sending to ThingsBoard
        """
        StatisticsService.count_connector_message(self._log.name, 'convertersMsgProcessed')
        basic_timestamp = int(time() * 1000)
        
        try:
            if not isinstance(configs, list):
                configs = [configs]
            if not isinstance(values, list):
                values = [values]
            
            converted_data = ConvertedData(
                device_name=self.__config['device_name'],
                device_type=self.__config['device_type']
            )
            
            # Get device report strategy
            device_report_strategy = None
            try:
                device_report_strategy = ReportStrategyConfig(
                    self.__config.get(REPORT_STRATEGY_PARAMETER)
                )
            except ValueError as e:
                self._log.trace(
                    f"Report strategy config is not specified for device {self.__config['device_name']}: {e}"
                )
            
            telemetry_batch = []
            attributes_batch = []
            
            for config, value_tuple in zip(configs, values):
                result, error = self.process_datapoint(
                    config, value_tuple, basic_timestamp, device_report_strategy
                )
                
                if result is not None:
                    if isinstance(result, TelemetryEntry):
                        telemetry_batch.append(result)
                    elif isinstance(result, dict):
                        attributes_batch.append(result)
            
            converted_data.add_to_telemetry(telemetry_batch)
            for attr in attributes_batch:
                converted_data.add_to_attributes(attr)
            
            StatisticsService.count_connector_message(
                self._log.name, 
                'convertersAttrProduced', 
                count=converted_data.attributes_datapoints_count
            )
            StatisticsService.count_connector_message(
                self._log.name, 
                'convertersTsProduced', 
                count=converted_data.telemetry_datapoints_count
            )
            
            return converted_data
            
        except Exception as e:
            self._log.exception(f"Error occurred while converting data: {e}")
            StatisticsService.count_connector_message(self._log.name, 'convertersMsgDropped')
            return ConvertedData(
                device_name=self.__config.get('device_name', 'Unknown'),
                device_type=self.__config.get('device_type', 'default')
            )
