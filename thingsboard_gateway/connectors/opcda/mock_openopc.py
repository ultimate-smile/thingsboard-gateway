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

"""
Mock OpenOPC implementation for development on non-Windows platforms.

This module provides a simulated OPC DA client that mimics the behavior of
OpenOPC without requiring Windows COM/DCOM dependencies. It's useful for:
- Development on macOS/Linux
- Unit testing
- CI/CD pipelines
- Documentation examples

WARNING: This is a simulation only. Use real OpenOPC on Windows for production.
"""

import random
import time
import logging
from datetime import datetime
from typing import List, Union, Tuple, Optional, Any


logger = logging.getLogger(__name__)


class MockOPCClient:
    """
    Mock OPC client that simulates OpenOPC behavior.
    
    Provides simulated tag data and basic OPC operations without
    requiring Windows or actual OPC DA server connection.
    """
    
    # OPC Quality codes
    OPC_QUALITY_GOOD = 192
    OPC_QUALITY_BAD = 0
    OPC_QUALITY_UNCERTAIN = 64
    
    def __init__(self):
        """Initialize mock OPC client."""
        self.connected = False
        self.server_name = None
        self.host = None
        self._session_start = None
        
        # Simulated tag database with dynamic value generators
        self.mock_tags = {
            # Random values
            'Random.Int1': lambda: random.randint(0, 255),
            'Random.Int2': lambda: random.randint(-32768, 32767),
            'Random.Int4': lambda: random.randint(0, 100),
            'Random.Real4': lambda: round(random.uniform(0.0, 100.0), 2),
            'Random.Real8': lambda: random.uniform(0.0, 100.0),
            'Random.String': lambda: f"Value_{random.randint(1, 100)}",
            'Random.Boolean': lambda: random.choice([True, False]),
            'Random.Time': lambda: datetime.now(),
            'Random.ArrayInt2': lambda: [random.randint(0, 100) for _ in range(5)],
            'Random.ArrayReal8': lambda: [random.uniform(0.0, 100.0) for _ in range(5)],
            
            # Bucket Brigade (simulated process values)
            'Bucket.Brigade.Int1': lambda: random.randint(0, 255),
            'Bucket.Brigade.Int2': lambda: random.randint(-1000, 1000),
            'Bucket.Brigade.Int4': lambda: random.randint(0, 10000),
            'Bucket.Brigade.Real4': lambda: round(random.uniform(-50.0, 150.0), 2),
            'Bucket.Brigade.Real8': lambda: random.uniform(-50.0, 150.0),
            'Bucket.Brigade.String': lambda: random.choice(['Running', 'Stopped', 'Alarm', 'Warning']),
            'Bucket.Brigade.Boolean': lambda: random.choice([True, False]),
            'Bucket.Brigade.Time': lambda: datetime.now(),
            'Bucket.Brigade.Money': lambda: round(random.uniform(0, 1000), 2),
            'Bucket.Brigade.UInt1': lambda: random.randint(0, 255),
            'Bucket.Brigade.UInt2': lambda: random.randint(0, 65535),
            'Bucket.Brigade.UInt4': lambda: random.randint(0, 100000),
            
            # Triangle Waves (sine/triangle patterns)
            'Triangle Waves.Int1': lambda: int(128 + 127 * self._sine_wave(period=10)),
            'Triangle Waves.Int2': lambda: int(16384 * self._sine_wave(period=15)),
            'Triangle Waves.Int4': lambda: int(50 + 50 * self._sine_wave(period=20)),
            'Triangle Waves.Real4': lambda: 50.0 + 50.0 * self._sine_wave(period=25),
            'Triangle Waves.Real8': lambda: 50.0 + 50.0 * self._sine_wave(period=30),
            
            # Saw-toothed Waves (linear ramp)
            'Saw-toothed Waves.Int1': lambda: int(255 * self._ramp_wave(period=10)),
            'Saw-toothed Waves.Int2': lambda: int(32767 * self._ramp_wave(period=15)),
            'Saw-toothed Waves.Int4': lambda: int(100 * self._ramp_wave(period=20)),
            'Saw-toothed Waves.Real4': lambda: 100.0 * self._ramp_wave(period=25),
            'Saw-toothed Waves.Real8': lambda: 100.0 * self._ramp_wave(period=30),
            
            # Square Waves (boolean patterns)
            'Square Waves.Boolean': lambda: self._square_wave(period=5),
            'Square Waves.Int1': lambda: 255 if self._square_wave(period=10) else 0,
            'Square Waves.Int2': lambda: 32767 if self._square_wave(period=15) else -32768,
            'Square Waves.Int4': lambda: 100 if self._square_wave(period=20) else 0,
        }
        
        # Writable tags storage
        self._written_values = {}
        
        logger.info("[MOCK OPC] Mock OPC client initialized")
    
    def _sine_wave(self, period: float = 10.0) -> float:
        """Generate sine wave value between -1 and 1."""
        import math
        if self._session_start is None:
            return 0.0
        elapsed = time.time() - self._session_start
        return math.sin(2 * math.pi * elapsed / period)
    
    def _ramp_wave(self, period: float = 10.0) -> float:
        """Generate ramp wave value between 0 and 1."""
        if self._session_start is None:
            return 0.0
        elapsed = time.time() - self._session_start
        return (elapsed % period) / period
    
    def _square_wave(self, period: float = 10.0) -> bool:
        """Generate square wave (boolean)."""
        if self._session_start is None:
            return False
        elapsed = time.time() - self._session_start
        return (elapsed % period) < (period / 2)
    
    def connect(self, server_name: str = 'Matrikon.OPC.Simulation.1', host: str = 'localhost') -> bool:
        """
        Simulate connection to OPC DA server.
        
        Args:
            server_name: OPC server ProgID (e.g., 'Matrikon.OPC.Simulation.1')
            host: Host address (e.g., 'localhost' or '192.168.1.100')
            
        Returns:
            True if connection successful
            
        Raises:
            Exception: If already connected
        """
        if self.connected:
            raise Exception("Already connected to OPC server")
        
        logger.info(f"[MOCK OPC] Connecting to {server_name} on {host}")
        self.server_name = server_name
        self.host = host
        self.connected = True
        self._session_start = time.time()
        
        # Simulate connection delay
        time.sleep(0.1)
        
        logger.info(f"[MOCK OPC] Successfully connected to {server_name}")
        return True
    
    def close(self) -> None:
        """Simulate disconnection from OPC server."""
        if not self.connected:
            logger.warning("[MOCK OPC] Not connected, nothing to close")
            return
        
        logger.info(f"[MOCK OPC] Disconnecting from {self.server_name}")
        self.connected = False
        self.server_name = None
        self.host = None
        self._session_start = None
        self._written_values.clear()
    
    def list(self, paths: str = '*', recursive: bool = False, 
             flat: bool = False, include_type: bool = False) -> List[Union[str, Tuple[str, str]]]:
        """
        Simulate listing OPC tags.
        
        Args:
            paths: Tag path pattern (e.g., '*', 'Random.*')
            recursive: Include subtags recursively
            flat: Return flat list
            include_type: Include data type information
            
        Returns:
            List of tag names or (tag, type) tuples
            
        Raises:
            Exception: If not connected
        """
        if not self.connected:
            raise Exception("Not connected to OPC server")
        
        # Filter tags based on pattern
        if paths == '*':
            tags = list(self.mock_tags.keys())
        else:
            # Simple pattern matching
            pattern = paths.replace('*', '')
            tags = [tag for tag in self.mock_tags.keys() if pattern in tag]
        
        if include_type:
            # Return with simulated type information
            result = []
            for tag in tags:
                if 'Real' in tag or 'Money' in tag:
                    data_type = 'VT_R8'
                elif 'Boolean' in tag:
                    data_type = 'VT_BOOL'
                elif 'String' in tag:
                    data_type = 'VT_BSTR'
                elif 'Array' in tag:
                    data_type = 'VT_ARRAY'
                else:
                    data_type = 'VT_I4'
                result.append((tag, data_type))
            return result
        
        return tags
    
    def read(self, tags: Union[str, List[str]], group: str = '', 
             sync: bool = True, source: str = 'device', 
             update: int = -1, timeout: int = 5000) -> Union[Tuple, List[Tuple]]:
        """
        Simulate reading tag values from OPC server.
        
        Args:
            tags: Single tag name or list of tag names
            group: OPC group name (not used in mock)
            sync: Synchronous read (not used in mock)
            source: Data source ('cache' or 'device')
            update: Update rate in ms (not used in mock)
            timeout: Read timeout in ms
            
        Returns:
            Tuple (tag_name, value, quality, timestamp) or list of tuples
            
        Raises:
            Exception: If not connected
        """
        if not self.connected:
            raise Exception("Not connected to OPC server")
        
        # Convert single tag to list
        single_tag = isinstance(tags, str)
        if single_tag:
            tags = [tags]
        
        results = []
        timestamp = datetime.now()
        
        for tag in tags:
            # Check if value was previously written
            if tag in self._written_values:
                value = self._written_values[tag]
                quality = self.OPC_QUALITY_GOOD
            elif tag in self.mock_tags:
                # Generate value using registered generator
                try:
                    value = self.mock_tags[tag]()
                    quality = self.OPC_QUALITY_GOOD
                except Exception as e:
                    logger.error(f"[MOCK OPC] Error generating value for {tag}: {e}")
                    value = None
                    quality = self.OPC_QUALITY_BAD
            else:
                # Tag not found
                logger.warning(f"[MOCK OPC] Tag not found: {tag}")
                value = None
                quality = self.OPC_QUALITY_BAD
            
            # Return format: (tag_name, value, quality, timestamp)
            results.append((tag, value, quality, timestamp))
            logger.debug(f"[MOCK OPC] Read {tag} = {value} (quality: {quality})")
        
        # Return single result if single tag was requested
        return results[0] if single_tag else results
    
    def write(self, tag_value_pairs: Union[Tuple[str, Any], List[Tuple[str, Any]]]) -> Union[Tuple, List[Tuple]]:
        """
        Simulate writing tag values to OPC server.
        
        Args:
            tag_value_pairs: Single (tag, value) tuple or list of tuples
            
        Returns:
            Tuple (tag, status) or list of tuples
            
        Raises:
            Exception: If not connected
        """
        if not self.connected:
            raise Exception("Not connected to OPC server")
        
        # Convert single pair to list
        single_pair = isinstance(tag_value_pairs, tuple) and len(tag_value_pairs) == 2
        if single_pair and isinstance(tag_value_pairs[0], str):
            tag_value_pairs = [tag_value_pairs]
        
        results = []
        for tag, value in tag_value_pairs:
            # Store written value
            self._written_values[tag] = value
            status = 'Success'
            
            logger.info(f"[MOCK OPC] Write {tag} = {value}")
            results.append((tag, status))
        
        # Return single result if single pair was requested
        return results[0] if single_pair else results
    
    def info(self) -> List[Tuple[str, Any]]:
        """
        Simulate getting OPC server information.
        
        Returns:
            List of (key, value) tuples with server information
            
        Raises:
            Exception: If not connected
        """
        if not self.connected:
            raise Exception("Not connected to OPC server")
        
        uptime = time.time() - self._session_start if self._session_start else 0
        
        return [
            ('Server Name', self.server_name or 'Unknown'),
            ('Host', self.host or 'localhost'),
            ('Version', '3.0 (Mock)'),
            ('Vendor', 'ThingsBoard Gateway Mock'),
            ('Status', 'Running'),
            ('Start Time', datetime.fromtimestamp(self._session_start).isoformat() if self._session_start else 'N/A'),
            ('Current Time', datetime.now().isoformat()),
            ('Uptime (seconds)', round(uptime, 2)),
            ('Mock Mode', True),
        ]
    
    def servers(self, host: str = 'localhost') -> List[str]:
        """
        Simulate listing available OPC servers.
        
        Args:
            host: Host to query for servers
            
        Returns:
            List of server ProgIDs
        """
        logger.info(f"[MOCK OPC] Listing servers on {host}")
        
        # Return common OPC server ProgIDs
        return [
            'Matrikon.OPC.Simulation.1',
            'Kepware.KEPServerEX.V6',
            'RSLinx.OPC.1',
            'Siemens.SIMATIC.OPC.DA.1',
        ]
    
    def add_mock_tag(self, tag_name: str, value_generator):
        """
        Add a custom mock tag with value generator.
        
        Args:
            tag_name: Tag name
            value_generator: Callable that returns tag value
        """
        self.mock_tags[tag_name] = value_generator
        logger.info(f"[MOCK OPC] Added mock tag: {tag_name}")
    
    def remove_mock_tag(self, tag_name: str) -> bool:
        """
        Remove a mock tag.
        
        Args:
            tag_name: Tag name
            
        Returns:
            True if tag was removed, False if not found
        """
        if tag_name in self.mock_tags:
            del self.mock_tags[tag_name]
            logger.info(f"[MOCK OPC] Removed mock tag: {tag_name}")
            return True
        return False


def client() -> MockOPCClient:
    """
    Create a mock OPC client instance.
    
    This is the main entry point that mimics OpenOPC.client().
    
    Returns:
        MockOPCClient instance
    """
    return MockOPCClient()


def open_client(host: str = 'localhost', port: int = 7766) -> MockOPCClient:
    """
    Create a mock OPC client with gateway connection.
    
    This mimics OpenOPC.open_client() for gateway mode.
    
    Args:
        host: Gateway host
        port: Gateway port
        
    Returns:
        MockOPCClient instance
    """
    logger.info(f"[MOCK OPC] Creating gateway client to {host}:{port}")
    return MockOPCClient()


# Module-level variables for compatibility
__version__ = '1.0.0-mock'
__author__ = 'ThingsBoard'


if __name__ == '__main__':
    """Example usage of mock OPC client."""
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print("=" * 60)
    print("Mock OpenOPC Client Demo")
    print("=" * 60)
    
    # Create client
    print("\n1. Creating OPC client...")
    opc = client()
    
    # Connect to server
    print("\n2. Connecting to OPC server...")
    opc.connect('Matrikon.OPC.Simulation.1', 'localhost')
    
    # Get server info
    print("\n3. Server information:")
    info = opc.info()
    for key, value in info:
        print(f"   {key}: {value}")
    
    # List tags
    print("\n4. Listing tags...")
    tags = opc.list('Random.*')
    print(f"   Found {len(tags)} tags:")
    for tag in tags[:5]:  # Show first 5
        print(f"   - {tag}")
    print(f"   ... and {len(tags) - 5} more")
    
    # Read single tag
    print("\n5. Reading single tag...")
    tag_name, value, quality, timestamp = opc.read('Random.Int4')
    print(f"   Tag: {tag_name}")
    print(f"   Value: {value}")
    print(f"   Quality: {quality}")
    print(f"   Timestamp: {timestamp}")
    
    # Read multiple tags
    print("\n6. Reading multiple tags...")
    results = opc.read(['Random.Int4', 'Random.Real8', 'Random.Boolean'])
    for tag_name, value, quality, timestamp in results:
        print(f"   {tag_name} = {value}")
    
    # Write tag
    print("\n7. Writing tag...")
    result = opc.write(('Random.Int4', 42))
    print(f"   Write result: {result}")
    
    # Read back written value
    print("\n8. Reading written value...")
    tag_name, value, quality, timestamp = opc.read('Random.Int4')
    print(f"   {tag_name} = {value} (should be 42)")
    
    # Close connection
    print("\n9. Closing connection...")
    opc.close()
    
    print("\n" + "=" * 60)
    print("Demo completed!")
    print("=" * 60)
