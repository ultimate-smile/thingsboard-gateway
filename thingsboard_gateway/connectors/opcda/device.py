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

from typing import List, Dict, Any, Optional

from thingsboard_gateway.gateway.constants import REPORT_STRATEGY_PARAMETER
from thingsboard_gateway.gateway.entities.report_strategy_config import ReportStrategyConfig


class OpcDaDevice:
    """Represents an OPC DA device with its configuration and tags."""
    
    def __init__(self, name: str, device_profile: str, config: dict, converter, logger):
        """
        Initialize OPC DA device.
        
        Args:
            name: Device name
            device_profile: Device profile/type
            config: Device configuration dictionary
            converter: Uplink converter instance
            logger: Logger instance
        """
        self._log = logger
        self.name = name
        self.device_profile = device_profile
        self.config = config
        self.converter = converter
        
        # Tags configuration
        self.tags: List[Dict[str, Any]] = []
        self.values = {
            'timeseries': [],
            'attributes': []
        }
        
        # Attribute updates configuration
        self.shared_attributes_keys = self.__get_shared_attributes_keys()
        self.shared_attributes_keys_value_pairs = self.__match_key_value_for_attribute_updates()
        
        # Report strategy
        self.report_strategy: Optional[ReportStrategyConfig] = None
        if self.config.get(REPORT_STRATEGY_PARAMETER):
            try:
                self.report_strategy = ReportStrategyConfig(
                    self.config.get(REPORT_STRATEGY_PARAMETER)
                )
            except ValueError as e:
                self._log.error(
                    f'Invalid report strategy config for {self.name}: {e}, '
                    'connector report strategy will be used'
                )
        
        # Load tags and values
        self.load_values()
    
    def __get_shared_attributes_keys(self) -> List[str]:
        """Extract shared attribute keys from configuration."""
        result = []
        for attr_config in self.config.get('attributes_updates', []):
            result.append(attr_config['key'])
        return result
    
    def __match_key_value_for_attribute_updates(self) -> Dict[str, str]:
        """Match keys to tag paths for attribute updates."""
        result = {}
        for attr_config in self.config.get('attributes_updates', []):
            result[attr_config['key']] = attr_config.get('tag') or attr_config.get('value')
        return result
    
    def load_values(self):
        """Load and parse tags configuration from device config."""
        self.tags = []
        
        for section in ('attributes', 'timeseries'):
            section_configs = self.config.get(section, [])
            
            for node_config in section_configs:
                try:
                    tag_path = node_config.get('tag') or node_config.get('value')
                    if not tag_path:
                        self._log.warning(
                            f"No tag specified for key '{node_config.get('key')}' in section '{section}'"
                        )
                        continue
                    
                    tag_config = {
                        'tag': tag_path,
                        'key': node_config['key'],
                        'section': section,
                        'timestampLocation': node_config.get('timestampLocation', 'gateway')
                    }
                    
                    # Add report strategy if specified
                    if node_config.get(REPORT_STRATEGY_PARAMETER):
                        tag_config[REPORT_STRATEGY_PARAMETER] = node_config[REPORT_STRATEGY_PARAMETER]
                    
                    self.values[section].append(tag_config)
                    self.tags.append(tag_config)
                    
                except KeyError as e:
                    self._log.error(
                        f'Invalid config for device {self.name}, '
                        f'section {section}: missing key {e}'
                    )
        
        self._log.debug(
            f'Loaded {len(self.tags)} tags for device {self.name} '
            f'({len(self.values["attributes"])} attributes, '
            f'{len(self.values["timeseries"])} timeseries)'
        )
    
    def get_tag_by_key(self, key: str) -> Optional[str]:
        """
        Get tag path by key name.
        
        Args:
            key: The key to search for
            
        Returns:
            Tag path string or None if not found
        """
        for tag_config in self.tags:
            if tag_config['key'] == key:
                return tag_config['tag']
        return None
    
    def get_all_tag_paths(self) -> List[str]:
        """
        Get all tag paths for this device.
        
        Returns:
            List of tag path strings
        """
        return [tag_config['tag'] for tag_config in self.tags]
    
    def __repr__(self):
        return (
            f'<OpcDaDevice> Name: {self.name}, '
            f'Profile: {self.device_profile}, '
            f'Tags: {len(self.tags)}'
        )
