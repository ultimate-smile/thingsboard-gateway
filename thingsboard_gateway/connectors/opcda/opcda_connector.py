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

import logging
from queue import Queue, Empty
from random import choice
from string import ascii_lowercase
from threading import Thread
from time import sleep, monotonic, time
from typing import Dict, List, Any, Optional

from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.connectors.opcda.device import OpcDaDevice
from thingsboard_gateway.gateway.constants import (
    CONNECTOR_PARAMETER, RECEIVED_TS_PARAMETER, CONVERTED_TS_PARAMETER,
    DATA_RETRIEVING_STARTED, REPORT_STRATEGY_PARAMETER
)
from thingsboard_gateway.gateway.entities.converted_data import ConvertedData
from thingsboard_gateway.gateway.entities.report_strategy_config import ReportStrategyConfig
from thingsboard_gateway.gateway.statistics.statistics_service import StatisticsService
from thingsboard_gateway.gateway.tb_gateway_service import TBGatewayService
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
from thingsboard_gateway.tb_utility.tb_logger import init_logger
from thingsboard_gateway.tb_utility.tb_utility import TBUtility

# Try import OpenOPC library with platform detection
import platform
import sys

PLATFORM = platform.system()
USE_MOCK_OPC = False
installation_required = False

# First, try to import OpenOPC
try:
    import OpenOPC
    # Test if pythoncom is available (Windows requirement)
    try:
        import pythoncom
        print(f"OpenOPC with pythoncom support detected (Platform: {PLATFORM})")
    except ImportError:
        if PLATFORM == 'Windows':
            # On Windows but pythoncom missing - this is an error
            print("ERROR: pythoncom not found on Windows. Please install pywin32:")
            print("  pip install pywin32")
            print("  python -m pywin32_postinstall -install")
            raise ImportError("pythoncom is required on Windows for OPC DA")
        else:
            # On non-Windows, pythoncom is expected to be missing
            print(f"Warning: Running on {PLATFORM}, pythoncom not available")
            print("Consider using OpenOPC Gateway Server on Windows or Mock mode for development")
except ImportError as import_err:
    installation_required = True
    print(f"OpenOPC not found: {import_err}")

# Install OpenOPC if needed
if installation_required:
    print("OPC DA library (OpenOPC) not found, attempting to install...")
    try:
        # On non-Windows, also suggest mock mode
        if PLATFORM != 'Windows':
            print(f"Note: You are on {PLATFORM}. OPC DA requires Windows or OpenOPC Gateway Server.")
            print("For development/testing, you can use Mock mode by setting useMockOpc: true in config")
        
        TBUtility.install_package("OpenOPC-Python3x")
        import OpenOPC
        
        # Try pywin32 on Windows
        if PLATFORM == 'Windows':
            try:
                import pythoncom
            except ImportError:
                print("Installing pywin32 for Windows COM support...")
                TBUtility.install_package("pywin32")
                print("Please run: python -m pywin32_postinstall -install")
    except Exception as e:
        print(f"Failed to install OpenOPC: {e}")
        print("Please install manually:")
        print("  pip install OpenOPC-Python3x")
        if PLATFORM == 'Windows':
            print("  pip install pywin32")
            print("  python -m pywin32_postinstall -install")
        else:
            print(f"Note: On {PLATFORM}, consider using:")
            print("  1. OpenOPC Gateway Server (runs on Windows)")
            print("  2. Mock mode for development (useMockOpc: true in config)")
            print("  3. Migrate to OPC UA for cross-platform support")

DEFAULT_UPLINK_CONVERTER = 'OpcDaUplinkConverter'


class OpcDaConnector(Connector, Thread):
    """OPC DA connector for ThingsBoard IoT Gateway."""
    
    def __init__(self, gateway: 'TBGatewayService', config: dict, connector_type: str):
        """
        Initialize OPC DA connector.
        
        Args:
            gateway: Gateway service instance
            config: Connector configuration dictionary
            connector_type: Type of connector (should be 'opcda')
        """
        self.statistics = {
            'MessagesReceived': 0,
            'MessagesSent': 0
        }
        super().__init__()
        
        self._connector_type = connector_type
        self.__gateway: 'TBGatewayService' = gateway
        self.__config = config
        self.__id = self.__config.get('id')
        self.name = self.__config.get(
            "name",
            'OPC-DA Connector ' + ''.join(choice(ascii_lowercase) for _ in range(5))
        )
        
        # Logging configuration
        self.__enable_remote_logging = self.__config.get('enableRemoteLogging', False)
        self.__log = init_logger(
            self.__gateway, self.name,
            self.__config.get('logLevel', 'INFO'),
            enable_remote_logging=self.__enable_remote_logging,
            is_connector_logger=True
        )
        self.__converter_log = init_logger(
            self.__gateway, self.name + '_converter',
            self.__config.get('logLevel', 'INFO'),
            enable_remote_logging=self.__enable_remote_logging,
            is_converter_logger=True,
            attr_name=self.name
        )
        
        # Report strategy configuration
        self.__connector_report_strategy_config = None
        if gateway.get_report_strategy_service() is not None:
            report_strategy = self.__config.get('reportStrategy')
            self.__connector_report_strategy_config = gateway.get_report_strategy_service().get_main_report_strategy()
            try:
                if report_strategy is not None:
                    self.__connector_report_strategy_config = ReportStrategyConfig(report_strategy)
            except ValueError as e:
                self.__log.warning(
                    'Error in report strategy configuration: %s, '
                    'the gateway main strategy will be used.', e
                )
        
        # Server configuration
        self.__server_conf = self.__config.get('server', {})
        self.__opc_server = self.__server_conf.get('name', 'Matrikon.OPC.Simulation.1')
        self.__opc_host = self.__server_conf.get('host', 'localhost')
        self.__use_mock_opc = self.__server_conf.get('useMockOpc', False)
        self.__opc_client: Optional[Any] = None
        
        # Check for mock mode
        if self.__use_mock_opc:
            self.__log.warning("Mock OPC mode enabled - using simulated OPC server")
            try:
                from thingsboard_gateway.connectors.opcda import mock_openopc
                global OpenOPC
                OpenOPC = mock_openopc
                global USE_MOCK_OPC
                USE_MOCK_OPC = True
                self.__log.info("Mock OpenOPC module loaded successfully")
            except ImportError as e:
                self.__log.error(f"Failed to load mock OpenOPC: {e}")
        elif PLATFORM != 'Windows':
            self.__log.warning(
                f"Running on {PLATFORM}. OPC DA typically requires Windows. "
                "If connection fails, consider:\n"
                "  1. Using OpenOPC Gateway Server (Windows)\n"
                "  2. Setting 'useMockOpc: true' for development\n"
                "  3. Migrating to OPC UA for cross-platform support"
            )
        
        # Polling configuration
        self.__poll_period = self.__server_conf.get('pollPeriodInMillis', 5000) / 1000
        self.__timeout = self.__server_conf.get('timeoutInMillis', 5000) / 1000
        
        # Data queue for conversion
        self.__data_to_convert = Queue(-1)
        
        # Device management
        self.__device_nodes: List[OpcDaDevice] = []
        self.__devices_by_name: Dict[str, OpcDaDevice] = {}
        
        # Connection state
        self.__connected = False
        self.__stopped = False
        self.daemon = True
        
        # Timing
        self.__next_poll = 0
        
        # Initialize devices from configuration
        self.__init_devices()
        
        # Start data conversion thread
        self.__conversion_thread = Thread(
            name='OPC DA Data Converter',
            target=self.__convert_data_worker,
            daemon=True
        )
        self.__conversion_thread.start()
        
        self.__log.info("OPC-DA Connector '%s' initialized", self.name)
    
    def __init_devices(self):
        """Initialize devices from configuration."""
        self.__log.debug("Initializing devices from configuration...")
        
        for device_config in self.__config.get('mapping', []):
            try:
                device_name = device_config.get('deviceInfo', {}).get('deviceNameExpression', 'Unknown Device')
                device_profile = device_config.get('deviceInfo', {}).get('deviceProfileExpression', 'default')
                
                # Load converter
                converter = self.__load_converter(device_config)
                if converter is None:
                    self.__log.error(f"Failed to load converter for device {device_name}")
                    continue
                
                # Create device config with name and type
                device_config_with_meta = {
                    **device_config,
                    'device_name': device_name,
                    'device_type': device_profile
                }
                
                # Create device instance
                device = OpcDaDevice(
                    name=device_name,
                    device_profile=device_profile,
                    config=device_config_with_meta,
                    converter=converter(device_config_with_meta, self.__converter_log),
                    logger=self.__log
                )
                
                self.__device_nodes.append(device)
                self.__devices_by_name[device_name] = device
                
                self.__log.info(f"Initialized device: {device_name} with {len(device.tags)} tags")
                
            except Exception as e:
                self.__log.exception(f"Error initializing device: {e}")
        
        self.__log.info(f"Initialized {len(self.__device_nodes)} devices")
    
    def __load_converter(self, device_config: dict):
        """Load converter module for device."""
        converter_class_name = device_config.get('converter')
        if not converter_class_name:
            self.__log.debug(
                f"No custom converter found for device {device_config.get('deviceInfo', {}).get('deviceNameExpression')}, "
                "using default converter"
            )
            converter_class_name = DEFAULT_UPLINK_CONVERTER
        
        module = TBModuleLoader.import_module(self._connector_type, converter_class_name)
        
        if module:
            self.__log.debug(f'Converter {converter_class_name} found!')
            return module
        
        self.__log.error(f"Cannot find converter {converter_class_name}")
        return None
    
    def open(self):
        """Start the connector."""
        self.__stopped = False
        self.start()
        self.__log.info("Starting OPC-DA Connector")
    
    def close(self):
        """Stop the connector."""
        self.__stopped = True
        self.__connected = False
        self.__log.info("Stopping OPC-DA Connector")
        
        # Disconnect from OPC server
        self.__disconnect()
        
        # Wait for thread to stop
        start_time = monotonic()
        while self.is_alive():
            if monotonic() - start_time > 10:
                self.__log.error("Failed to stop connector %s", self.get_name())
                break
            sleep(0.1)
        
        self.__log.info('%s has been stopped.', self.get_name())
        self.__log.stop()
    
    def get_id(self):
        """Get connector ID."""
        return self.__id
    
    def get_name(self):
        """Get connector name."""
        return self.name
    
    def get_type(self):
        """Get connector type."""
        return self._connector_type
    
    def get_config(self):
        """Get connector configuration."""
        return self.__config
    
    def is_connected(self):
        """Check if connector is connected."""
        return self.__connected
    
    def is_stopped(self):
        """Check if connector is stopped."""
        return self.__stopped
    
    def run(self):
        """Main connector loop."""
        while not self.__stopped:
            try:
                # Connect to OPC server if not connected
                if not self.__connected:
                    if self.__connect():
                        self.__log.info(f"Connected to OPC DA server: {self.__opc_server}")
                        self.__connected = True
                    else:
                        self.__log.error("Failed to connect to OPC DA server, retrying in 10 seconds...")
                        sleep(10)
                        continue
                
                # Poll data if it's time
                if monotonic() >= self.__next_poll:
                    self.__next_poll = monotonic() + self.__poll_period
                    self.__poll_devices()
                
                # Sleep until next poll
                time_to_sleep = max(0, self.__next_poll - monotonic())
                if time_to_sleep > 0:
                    sleep(min(time_to_sleep, 1.0))
                else:
                    sleep(0.1)
                    
            except Exception as e:
                self.__log.exception(f"Error in main loop: {e}")
                self.__connected = False
                self.__disconnect()
                sleep(5)
    
    def __connect(self) -> bool:
        """
        Connect to OPC DA server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            self.__log.info(f"Connecting to OPC DA server '{self.__opc_server}' on host '{self.__opc_host}'...")
            
            # Check if mock mode is active
            if USE_MOCK_OPC or self.__use_mock_opc:
                self.__log.info("Using Mock OPC client")
            
            self.__opc_client = OpenOPC.client()
            self.__opc_client.connect(self.__opc_server, self.__opc_host)
            
            # Test connection by getting server info
            try:
                info = self.__opc_client.info()
                self.__log.debug(f"OPC Server info: {info}")
            except Exception as e:
                self.__log.debug(f"Could not retrieve server info: {e}")
            
            return True
            
        except NameError as ne:
            # Catch specific pythoncom errors
            if 'pythoncom' in str(ne):
                self.__log.error(
                    "pythoncom is not defined! This usually means:\n"
                    "  1. On Windows: pywin32 is not installed or not configured properly\n"
                    "     Solution: pip install pywin32 && python -m pywin32_postinstall -install\n"
                    "  2. On macOS/Linux: OPC DA requires Windows or OpenOPC Gateway Server\n"
                    "     Solutions:\n"
                    "       - Use OpenOPC Gateway Server running on Windows\n"
                    "       - Enable mock mode: set 'useMockOpc: true' in server config\n"
                    "       - Consider migrating to OPC UA (cross-platform)\n"
                    f"  Current platform: {PLATFORM}"
                )
            else:
                self.__log.error(f"NameError during connection: {ne}")
            self.__opc_client = None
            return False
            
        except Exception as e:
            error_msg = str(e)
            
            # Provide helpful error messages
            if 'pythoncom' in error_msg.lower():
                self.__log.error(
                    f"pythoncom error: {e}\n"
                    "This indicates a Windows COM/DCOM issue. Check:\n"
                    "  - pywin32 is installed: pip list | grep pywin32\n"
                    "  - pywin32 is configured: python -m pywin32_postinstall -install\n"
                    "  - Running on Windows (OPC DA requires Windows)\n"
                    f"Current platform: {PLATFORM}"
                )
            elif 'com_error' in error_msg.lower() or 'invalid class string' in error_msg.lower():
                self.__log.error(
                    f"OPC Server error: {e}\n"
                    "This indicates the OPC server is not registered or accessible. Check:\n"
                    f"  - OPC Server '{self.__opc_server}' is installed\n"
                    "  - OPC Server is running\n"
                    "  - ProgID is correct (use OPC Enum to list servers)\n"
                    "  - DCOM permissions are configured correctly"
                )
            else:
                self.__log.error(f"Failed to connect to OPC DA server: {e}")
            
            self.__opc_client = None
            return False
    
    def __disconnect(self):
        """Disconnect from OPC DA server."""
        if self.__opc_client:
            try:
                self.__opc_client.close()
                self.__log.info("Disconnected from OPC DA server")
            except Exception as e:
                self.__log.warning(f"Error disconnecting from OPC DA server: {e}")
            finally:
                self.__opc_client = None
    
    def __poll_devices(self):
        """Poll all devices for data."""
        if not self.__connected or not self.__opc_client:
            return
        
        data_retrieving_started = int(time() * 1000)
        received_ts = int(time() * 1000)
        
        for device in self.__device_nodes:
            try:
                # Get all tag paths for this device
                tag_paths = device.get_all_tag_paths()
                if not tag_paths:
                    continue
                
                # Read tags from OPC server
                # OpenOPC read returns list of tuples: (tag_name, value, quality, timestamp)
                values = self.__opc_client.read(tag_paths, group='')
                
                # Queue data for conversion
                self.__data_to_convert.put((device, values, received_ts, data_retrieving_started))
                
                StatisticsService.count_connector_message(
                    self.name,
                    stat_parameter_name='connectorMsgsReceived'
                )
                
            except Exception as e:
                self.__log.error(f"Error polling device {device.name}: {e}")
                # Try to reconnect on next iteration
                if "not connected" in str(e).lower():
                    self.__connected = False
    
    def __convert_data_worker(self):
        """Worker thread for data conversion."""
        while not self.__stopped:
            try:
                # Get data from queue with timeout
                try:
                    device, raw_values, received_ts, data_retrieving_started = \
                        self.__data_to_convert.get(timeout=1.0)
                except Empty:
                    continue
                
                # Convert raw values to the format expected by converter
                # raw_values is list of tuples: (tag_name, value, quality, timestamp)
                configs = device.tags
                values = []
                
                for raw_value in raw_values:
                    if isinstance(raw_value, tuple) and len(raw_value) >= 4:
                        # Format: (tag_name, value, quality, timestamp)
                        _, value, quality, timestamp = raw_value[0:4]
                        values.append((value, quality, timestamp))
                    else:
                        self.__log.warning(f"Unexpected value format: {raw_value}")
                        values.append((None, 0, None))
                
                # Convert data
                converted_data: ConvertedData = device.converter.convert(configs, values)
                
                if converted_data:
                    # Add metadata
                    converted_data.add_to_metadata({
                        CONNECTOR_PARAMETER: self.get_name(),
                        RECEIVED_TS_PARAMETER: received_ts,
                        CONVERTED_TS_PARAMETER: int(time() * 1000),
                        DATA_RETRIEVING_STARTED: data_retrieving_started
                    })
                    
                    # Send to gateway
                    self.__gateway.send_to_storage(self.get_name(), self.get_id(), converted_data)
                    
                    StatisticsService.count_connector_message(
                        self.name,
                        stat_parameter_name='connectorMsgsSent'
                    )
                    StatisticsService.count_connector_bytes(
                        self.name,
                        converted_data,
                        stat_parameter_name='connectorBytesReceived'
                    )
                    
            except Exception as e:
                self.__log.exception(f"Error in data conversion worker: {e}")
    
    def on_attributes_update(self, content: Dict):
        """
        Handle attribute updates from ThingsBoard.
        
        Args:
            content: Update content containing device name and attributes
        """
        self.__log.debug(f"Received attribute update: {content}")
        
        try:
            device_name = content.get('device')
            device = self.__devices_by_name.get(device_name)
            
            if device is None:
                self.__log.error(f'Device {device_name} not found for attributes update')
                return
            
            if not device.config.get('attributes_updates'):
                self.__log.warning(f"No attribute updates configuration for device {device_name}")
                return
            
            # Process each attribute
            for key, value in content.get('data', {}).items():
                tag_path = device.shared_attributes_keys_value_pairs.get(key)
                
                if not tag_path:
                    self.__log.warning(
                        f"No tag mapping found for attribute key '{key}' on device '{device_name}'"
                    )
                    continue
                
                # Write value to OPC server
                self.__write_tag(tag_path, value)
                
        except Exception as e:
            self.__log.exception(f"Error handling attribute update: {e}")
    
    def server_side_rpc_handler(self, content: Dict):
        """
        Handle RPC requests from ThingsBoard.
        
        Args:
            content: RPC request content
            
        Returns:
            RPC response dictionary
        """
        self.__log.info(f'Received server side RPC request: {content}')
        
        try:
            device_name = content.get('device')
            device = self.__devices_by_name.get(device_name)
            
            if device is None:
                error_msg = f'Device {device_name} not found'
                self.__log.error(error_msg)
                return {'error': error_msg, 'success': False}
            
            method = content.get('data', {}).get('method')
            params = content.get('data', {}).get('params')
            
            if method == 'read':
                # Read tag value
                tag_path = params.get('tag') if isinstance(params, dict) else params
                return self.__read_tag(tag_path)
                
            elif method == 'write':
                # Write tag value
                if not isinstance(params, dict):
                    return {'error': 'Invalid params format', 'success': False}
                
                tag_path = params.get('tag')
                value = params.get('value')
                return self.__write_tag(tag_path, value)
                
            else:
                return {'error': f'Unknown method: {method}', 'success': False}
                
        except Exception as e:
            self.__log.exception(f'Error handling RPC request: {e}')
            return {'error': str(e), 'success': False}
    
    def __read_tag(self, tag_path: str) -> Dict:
        """
        Read a tag value from OPC server.
        
        Args:
            tag_path: OPC tag path
            
        Returns:
            Dictionary with result or error
        """
        try:
            if not self.__connected or not self.__opc_client:
                return {'error': 'Not connected to OPC server', 'success': False}
            
            result = self.__opc_client.read(tag_path)
            
            if isinstance(result, tuple) and len(result) >= 2:
                value, quality = result[0:2]
                return {
                    'value': value,
                    'quality': quality,
                    'success': True
                }
            else:
                return {'value': result, 'success': True}
                
        except Exception as e:
            self.__log.error(f"Error reading tag '{tag_path}': {e}")
            return {'error': str(e), 'success': False}
    
    def __write_tag(self, tag_path: str, value: Any) -> Dict:
        """
        Write a value to OPC server tag.
        
        Args:
            tag_path: OPC tag path
            value: Value to write
            
        Returns:
            Dictionary with result or error
        """
        try:
            if not self.__connected or not self.__opc_client:
                return {'error': 'Not connected to OPC server', 'success': False}
            
            self.__opc_client.write((tag_path, value))
            self.__log.info(f"Successfully wrote value {value} to tag '{tag_path}'")
            
            return {'success': True, 'value': value}
            
        except Exception as e:
            self.__log.error(f"Error writing tag '{tag_path}': {e}")
            return {'error': str(e), 'success': False}
