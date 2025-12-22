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

import time
from copy import deepcopy
from random import choice
from string import ascii_lowercase
from threading import Thread
from queue import Queue

from simplejson import dumps

from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
from thingsboard_gateway.tb_utility.tb_utility import TBUtility
from thingsboard_gateway.gateway.statistics_service import StatisticsService
from thingsboard_gateway.tb_utility.tb_logger import init_logger

# Try to import OpenOPC library or provide installation instructions
try:
    import OpenOPC
except ImportError:
    print("OPC-DA library (OpenOPC) not found")
    print("To use OPC DA connector, install OpenOPC:")
    print("  pip install OpenOPC-Python3x")
    print("  or pip install pywin32 (for Windows)")
    OpenOPC = None

from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.connectors.opcda.opcda_uplink_converter import OpcDaUplinkConverter


class OpcDaConnector(Thread, Connector):
    def __init__(self, gateway, config, connector_type):
        self._connector_type = connector_type
        self.statistics = {
            'MessagesReceived': 0,
            'MessagesSent': 0
        }
        super().__init__()
        self.__gateway = gateway
        self._config = config
        self.__id = self._config.get('id')
        self.__server_conf = config.get("server")
        self.name = self._config.get(
            "name",
            'OPC-DA ' + ''.join(choice(ascii_lowercase) for _ in range(5)) + " Connector"
        )
        self._log = init_logger(
            self.__gateway,
            self.name,
            self._config.get('logLevel', 'INFO'),
            enable_remote_logging=self._config.get('enableRemoteLogging', False)
        )
        
        # Check if OpenOPC is available
        if OpenOPC is None:
            self._log.error("OpenOPC library is not installed. OPC DA connector cannot start.")
            self._log.error("Please install: pip install OpenOPC-Python3x")
            self.__stopped = True
            return
        
        self.__interest_tags = []
        self.__available_object_resources = {}
        self.__previous_scan_time = 0
        
        # Parse mapping configuration
        for mapping in self.__server_conf.get("mapping", []):
            if mapping.get("deviceNodePattern") is not None:
                self.__interest_tags.append({mapping["deviceNodePattern"]: mapping})
            else:
                self._log.error(
                    "deviceNodePattern in mapping: %s - not found, add property deviceNodePattern to processing this mapping",
                    dumps(mapping)
                )
        
        # Server connection parameters
        self.__server_name = self.__server_conf.get("name", "")
        self.__host = self.__server_conf.get("host", "localhost")
        
        self.client = None
        self.__connected = False
        self.__stopped = False
        self.data_to_send = []
        self.daemon = True
        
        # Subscription and polling settings
        self.__poll_period = self.__server_conf.get("pollPeriodInMillis", 5000) / 1000.0
        self.__disable_subscriptions = self.__server_conf.get("disableSubscriptions", True)

    def is_connected(self):
        return self.__connected

    def is_stopped(self):
        return self.__stopped

    def get_type(self):
        return self._connector_type

    def open(self):
        self.__stopped = False
        self.start()
        self._log.info("Starting OPC-DA Connector")

    def __create_client(self):
        """Create OPC DA client connection"""
        if self.client:
            try:
                self.client.close()
            except:
                pass
            self.client = None
        
        try:
            self.client = OpenOPC.client()
            self._log.debug("OPC DA client created")
        except Exception as e:
            self._log.error("Failed to create OPC DA client: %s", e)
            self.client = None
            raise

    def __connect(self):
        """Connect to OPC DA server"""
        self.__create_client()
        
        while not self.__connected and not self.__stopped:
            try:
                # Connect to OPC DA server
                if self.__host and self.__host != "localhost":
                    self.client.connect(self.__server_name, self.__host)
                else:
                    self.client.connect(self.__server_name)
                
                self._log.info("Connected to OPC DA server: %s on %s", 
                             self.__server_name, self.__host)
                
                # Get server info
                try:
                    server_info = self.client.info()
                    self._log.debug("Server info: %s", server_info)
                except:
                    pass
                
                self.__connected = True
                self.__initialize_client()
                
            except Exception as e:
                self._log.error("Error connecting to OPC DA server %s: %s", 
                              self.__server_name, e)
                time.sleep(10)

    def __initialize_client(self):
        """Initialize client and scan configured tags"""
        self._log.debug("Initializing OPC DA client...")
        self.scan_tags_from_config()
        self.__previous_scan_time = time.time() * 1000
        self._log.debug("Available resources: %s", self.__available_object_resources)

    def run(self):
        """Main connector loop"""
        while not self.__stopped:
            try:
                time.sleep(0.2)
                self.__check_connection()
                
                if not self.__connected and not self.__stopped:
                    self.__connect()
                elif not self.__stopped:
                    current_time = time.time() * 1000
                    
                    # Poll data at specified intervals
                    if current_time - self.__previous_scan_time > (self.__poll_period * 1000):
                        self.scan_tags_from_config()
                        self.__previous_scan_time = current_time
                    
                    # Send collected data to gateway
                    while self.data_to_send:
                        self.__gateway.send_to_storage(
                            self.get_name(),
                            self.get_id(),
                            self.data_to_send.pop(0)
                        )
                
                if self.__stopped:
                    self.close()
                    break
                    
            except (KeyboardInterrupt, SystemExit):
                self.close()
                raise
            except Exception as e:
                self._log.error("Error in main loop: %s", e)
                time.sleep(10)

    def __check_connection(self):
        """Check if connection to OPC DA server is still alive"""
        try:
            if self.client:
                # Try to read server status
                self.client.ping()
                self.__connected = True
            else:
                self.__connected = False
        except:
            self.__connected = False

    def scan_tags_from_config(self):
        """Scan and read tags configured in mapping"""
        try:
            if not self.__interest_tags:
                return
            
            for device_object in self.__interest_tags:
                for current_device in device_object:
                    try:
                        device_configuration = device_object[current_device]
                        devices_info_array = self.__search_general_info(device_configuration)
                        
                        for device_info in devices_info_array:
                            if device_info is not None:
                                self.__read_tags_and_send(device_info)
                                self.__save_rpc_methods(device_info)
                                self.__search_attribute_update_tags(device_info)
                            else:
                                self._log.error("Device info is None")
                                
                    except Exception as e:
                        self._log.exception("Error scanning device: %s", e)
                        
        except Exception as e:
            self._log.exception("Error in scan_tags_from_config: %s", e)

    def __search_general_info(self, device_config):
        """Extract device information from configuration"""
        result = []
        
        try:
            device_name_pattern = device_config.get("deviceNamePattern", "OPC-DA Device")
            device_type_pattern = device_config.get("deviceTypePattern", "default")
            
            # For OPC DA, we don't browse nodes like OPC UA
            # We directly use the device name from config
            device_name = TBUtility.get_value(device_name_pattern, get_tag=True)
            device_type = TBUtility.get_value(device_type_pattern, get_tag=True)
            
            result_device_dict = {
                "deviceName": device_name,
                "deviceType": device_type,
                "configuration": deepcopy(device_config)
            }
            
            result.append(result_device_dict)
            
        except Exception as e:
            self._log.exception("Error in __search_general_info: %s", e)
        
        return result

    def __read_tags_and_send(self, device_info):
        """Read tags and send data to ThingsBoard"""
        information_types = {"attributes": "attributes", "timeseries": "telemetry"}
        tags_to_read = []
        tag_configs = {}
        
        try:
            # Collect all tags to read
            for information_type in information_types:
                for information in device_info["configuration"].get(information_type, []):
                    tag = information.get("tag", information.get("key", ""))
                    if tag:
                        tags_to_read.append(tag)
                        tag_configs[tag] = (information, information_type)
            
            if not tags_to_read:
                return
            
            # Read all tags at once
            try:
                tag_values = self.client.read(tags_to_read)
                
                # Process each tag value
                if not isinstance(tag_values, list):
                    tag_values = [tag_values]
                
                # Get or create converter
                if device_info.get("uplink_converter") is None:
                    configuration = {
                        **device_info["configuration"],
                        "deviceName": device_info["deviceName"],
                        "deviceType": device_info["deviceType"]
                    }
                    
                    if device_info["configuration"].get('converter') is None:
                        converter = OpcDaUplinkConverter(configuration, self._log)
                    else:
                        converter = TBModuleLoader.import_module(
                            self._connector_type,
                            device_info["configuration"].get('converter')
                        )(configuration, self._log)
                    
                    device_info["uplink_converter"] = converter
                else:
                    converter = device_info["uplink_converter"]
                
                # Process read values
                for tag_data in tag_values:
                    if len(tag_data) >= 3:
                        tag_name, value, quality, timestamp = tag_data[0], tag_data[1], tag_data[2], tag_data[3] if len(tag_data) > 3 else None
                    else:
                        continue
                    
                    if tag_name in tag_configs:
                        information, information_type = tag_configs[tag_name]
                        
                        # Convert and send data
                        try:
                            converted_data = converter.convert(
                                (information, information_type),
                                value,
                                quality,
                                timestamp
                            )
                            
                            self.statistics['MessagesReceived'] += 1
                            self.data_to_send.append(converted_data)
                            self.statistics['MessagesSent'] += 1
                            
                            self._log.debug("Data to ThingsBoard: %s", converted_data)
                            
                        except Exception as e:
                            self._log.error("Error converting data for tag %s: %s", tag_name, e)
                
            except Exception as e:
                self._log.error("Error reading tags: %s", e)
                
        except Exception as e:
            self._log.exception("Error in __read_tags_and_send: %s", e)

    def __save_rpc_methods(self, device_info):
        """Save RPC methods configuration"""
        try:
            device_name = device_info["deviceName"]
            
            if self.__available_object_resources.get(device_name) is None:
                self.__available_object_resources[device_name] = {}
            
            if self.__available_object_resources[device_name].get("methods") is None:
                self.__available_object_resources[device_name]["methods"] = []
            
            for method_config in device_info["configuration"].get("rpc_methods", []):
                self.__available_object_resources[device_name]["methods"].append(method_config)
                
        except Exception as e:
            self._log.exception("Error in __save_rpc_methods: %s", e)

    def __search_attribute_update_tags(self, device_info):
        """Configure tags for attribute updates"""
        try:
            device_name = device_info["deviceName"]
            
            if self.__available_object_resources.get(device_name) is None:
                self.__available_object_resources[device_name] = {}
            
            if self.__available_object_resources[device_name].get("variables") is None:
                self.__available_object_resources[device_name]["variables"] = []
            
            for attribute_update in device_info["configuration"].get("attributes_updates", []):
                tag = attribute_update.get("attributeOnDevice", "")
                if tag:
                    self.__available_object_resources[device_name]["variables"].append({
                        attribute_update["attributeOnThingsBoard"]: tag
                    })
                    
        except Exception as e:
            self._log.exception("Error in __search_attribute_update_tags: %s", e)

    def close(self):
        """Close connector and disconnect from server"""
        self.__stopped = True
        if self.client:
            try:
                self.client.close()
            except:
                pass
        self.__connected = False
        self._log.info('%s has been stopped.', self.get_name())
        self._log.reset()

    def get_id(self):
        return self.__id

    def get_name(self):
        return self.name

    def get_config(self):
        return self.__server_conf

    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')
    def on_attributes_update(self, content):
        """Handle attribute updates from ThingsBoard"""
        self._log.debug("Attribute update received: %s", content)
        try:
            device_name = content.get("device")
            if not device_name or device_name not in self.__available_object_resources:
                self._log.warning("Device %s not found in resources", device_name)
                return
            
            variables = self.__available_object_resources[device_name].get('variables', [])
            
            for attribute in content.get("data", {}):
                for variable_map in variables:
                    if attribute in variable_map:
                        tag = variable_map[attribute]
                        value = content["data"][attribute]
                        
                        try:
                            # Write value to OPC DA tag
                            self.client.write((tag, value))
                            self._log.debug("Written value %s to tag %s", value, tag)
                        except Exception as e:
                            self._log.error("Error writing to tag %s: %s", tag, e)
                            
        except Exception as e:
            self._log.exception("Error in on_attributes_update: %s", e)

    @StatisticsService.CollectAllReceivedBytesStatistics(start_stat_type='allReceivedBytesFromTB')
    def server_side_rpc_handler(self, content):
        """Handle RPC requests from ThingsBoard"""
        try:
            if content.get('data') is None:
                content['data'] = {
                    'params': content.get('params', {}),
                    'method': content.get('method', '')
                }
            
            rpc_method = content["data"].get("method")
            device = content.get("device")
            
            # Check if RPC type is connector RPC
            try:
                connector_type, rpc_method_name = rpc_method.split('_')
                if connector_type == self._connector_type:
                    rpc_method = rpc_method_name
                    device = content['params'].split(' ')[0].split('=')[-1]
            except (ValueError, IndexError):
                pass
            
            # Handle get/set methods
            if rpc_method == 'get':
                self.__handle_rpc_get(content, device)
            elif rpc_method == 'set':
                self.__handle_rpc_set(content, device)
            else:
                # Handle custom RPC methods
                self.__handle_custom_rpc(content, device, rpc_method)
                
        except Exception as e:
            self._log.exception("Error in server_side_rpc_handler: %s", e)

    def __handle_rpc_get(self, content, device):
        """Handle RPC get request"""
        try:
            params = content['data'].get('params', '')
            if isinstance(params, str):
                tag = params
            elif isinstance(params, dict):
                tag = params.get('tag', '')
            else:
                tag = str(params)
            
            # Read tag value
            result = self.client.read(tag)
            
            if result:
                value = result[1] if len(result) > 1 else None
                self.__gateway.send_rpc_reply(
                    device=device,
                    req_id=content['data'].get('id'),
                    content={rpc_method: value, 'code': 200}
                )
            else:
                self.__gateway.send_rpc_reply(
                    device=device,
                    req_id=content['data'].get('id'),
                    content={'error': 'Failed to read tag', 'code': 500}
                )
                
        except Exception as e:
            self._log.error("Error in RPC get: %s", e)
            self.__gateway.send_rpc_reply(
                device=device,
                req_id=content['data'].get('id'),
                content={'error': str(e), 'code': 500}
            )

    def __handle_rpc_set(self, content, device):
        """Handle RPC set request"""
        try:
            params = content['data'].get('params', {})
            
            if isinstance(params, dict):
                tag = params.get('tag', '')
                value = params.get('value')
            else:
                # Parse string format: "tag=xxx;value=yyy"
                parts = str(params).split(';')
                tag = None
                value = None
                for part in parts:
                    if '=' in part:
                        k, v = part.split('=', 1)
                        if k.strip() == 'tag':
                            tag = v.strip()
                        elif k.strip() == 'value':
                            value = v.strip()
            
            if tag and value is not None:
                # Write value to tag
                self.client.write((tag, value))
                self.__gateway.send_rpc_reply(
                    device=device,
                    req_id=content['data'].get('id'),
                    content={'success': True, 'code': 200}
                )
            else:
                self.__gateway.send_rpc_reply(
                    device=device,
                    req_id=content['data'].get('id'),
                    content={'error': 'Invalid parameters', 'code': 400}
                )
                
        except Exception as e:
            self._log.error("Error in RPC set: %s", e)
            self.__gateway.send_rpc_reply(
                device=device,
                req_id=content['data'].get('id'),
                content={'error': str(e), 'code': 500}
            )

    def __handle_custom_rpc(self, content, device, rpc_method):
        """Handle custom RPC methods"""
        try:
            if device not in self.__available_object_resources:
                self._log.error("Device %s not found", device)
                self.__gateway.send_rpc_reply(
                    device=device,
                    req_id=content['data'].get('id'),
                    content={'error': 'Device not found', 'code': 404}
                )
                return
            
            methods = self.__available_object_resources[device].get('methods', [])
            method_found = False
            
            for method_config in methods:
                if method_config.get('method') == rpc_method:
                    method_found = True
                    tag = method_config.get('tag', '')
                    value = content['data'].get('params', method_config.get('value'))
                    
                    if tag:
                        # Write value to tag
                        self.client.write((tag, value))
                        self.__gateway.send_rpc_reply(
                            device=device,
                            req_id=content['data'].get('id'),
                            content={rpc_method: 'success', 'code': 200}
                        )
                    break
            
            if not method_found:
                self.__gateway.send_rpc_reply(
                    device=device,
                    req_id=content['data'].get('id'),
                    content={'error': f'Method {rpc_method} not found', 'code': 404}
                )
                
        except Exception as e:
            self._log.error("Error in custom RPC: %s", e)
            self.__gateway.send_rpc_reply(
                device=device,
                req_id=content['data'].get('id'),
                content={'error': str(e), 'code': 500}
            )

    def update_converter_config(self, converter_name, config):
        """Update converter configuration"""
        self._log.debug(
            'Received remote converter configuration update for %s with configuration %s',
            converter_name, config
        )
        # Implementation for updating converter config if needed
        pass
