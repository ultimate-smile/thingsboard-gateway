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

import unittest
from unittest.mock import Mock
from datetime import datetime

from thingsboard_gateway.connectors.opcda.opcda_uplink_converter import OpcDaUplinkConverter


class TestOpcDaUplinkConverter(unittest.TestCase):
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Mock()
        self.config = {
            "deviceName": "TestDevice",
            "deviceType": "Sensor"
        }
        self.converter = OpcDaUplinkConverter(self.config, self.logger)
    
    def test_convert_timeseries_integer(self):
        """Test converting integer timeseries data"""
        information = {
            "key": "temperature",
            "tag": "Channel1.Device1.Temperature",
            "type": "int"
        }
        information_type = "timeseries"
        value = 25.7
        
        result = self.converter.convert(
            (information, information_type),
            value
        )
        
        self.assertEqual(result["deviceName"], "TestDevice")
        self.assertEqual(result["deviceType"], "Sensor")
        self.assertEqual(len(result["telemetry"]), 1)
        self.assertIn("ts", result["telemetry"][0])
        self.assertEqual(result["telemetry"][0]["values"]["temperature"], 25)
    
    def test_convert_timeseries_float(self):
        """Test converting float timeseries data"""
        information = {
            "key": "pressure",
            "tag": "Channel1.Device1.Pressure",
            "type": "double"
        }
        information_type = "timeseries"
        value = 101.325
        
        result = self.converter.convert(
            (information, information_type),
            value
        )
        
        self.assertEqual(result["telemetry"][0]["values"]["pressure"], 101.325)
    
    def test_convert_attribute_string(self):
        """Test converting string attribute data"""
        information = {
            "key": "model",
            "tag": "Device.Model",
            "type": "string"
        }
        information_type = "attributes"
        value = "ABC-123"
        
        result = self.converter.convert(
            (information, information_type),
            value
        )
        
        self.assertEqual(len(result["attributes"]), 1)
        self.assertEqual(result["attributes"][0]["model"], "ABC-123")
    
    def test_convert_attribute_boolean(self):
        """Test converting boolean attribute data"""
        information = {
            "key": "status",
            "tag": "Device.Status",
            "type": "bool"
        }
        information_type = "attributes"
        value = 1
        
        result = self.converter.convert(
            (information, information_type),
            value
        )
        
        self.assertEqual(result["attributes"][0]["status"], True)
    
    def test_convert_with_timestamp(self):
        """Test converting data with custom timestamp"""
        information = {
            "key": "value",
            "tag": "Device.Value",
            "type": "int"
        }
        information_type = "timeseries"
        value = 100
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        result = self.converter.convert(
            (information, information_type),
            value,
            timestamp=timestamp
        )
        
        expected_ts = int(timestamp.timestamp() * 1000)
        self.assertEqual(result["telemetry"][0]["ts"], expected_ts)
    
    def test_convert_without_type_conversion(self):
        """Test converting data without type specification"""
        information = {
            "key": "rawValue",
            "tag": "Device.RawValue"
        }
        information_type = "attributes"
        value = "test_value"
        
        result = self.converter.convert(
            (information, information_type),
            value
        )
        
        self.assertEqual(result["attributes"][0]["rawValue"], "test_value")
    
    def test_convert_invalid_type_conversion(self):
        """Test handling invalid type conversion gracefully"""
        information = {
            "key": "value",
            "tag": "Device.Value",
            "type": "int"
        }
        information_type = "attributes"
        value = "not_a_number"
        
        result = self.converter.convert(
            (information, information_type),
            value
        )
        
        # Should use original value when conversion fails
        self.assertEqual(result["attributes"][0]["value"], "not_a_number")
    
    def test_config_property(self):
        """Test config property getter and setter"""
        new_config = {"deviceName": "NewDevice"}
        self.converter.config = new_config
        self.assertEqual(self.converter.config, new_config)


if __name__ == '__main__':
    unittest.main()
