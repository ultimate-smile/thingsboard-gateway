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
Example Connector Plugin

这是一个示例连接器插件，展示了如何创建一个基本的连接器。
这个连接器会定期发送模拟数据到ThingsBoard。
"""

import logging
import random
import time
from threading import Thread
from typing import Dict, Any

from thingsboard_gateway.connectors.connector import Connector
from thingsboard_gateway.gateway.constants import CONNECTOR_PARAMETER

log = logging.getLogger(__name__)


class ExampleConnector(Connector):
    """
    示例连接器实现
    
    这个连接器展示了一个完整的连接器实现，包括：
    - 连接生命周期管理
    - 定期数据采集
    - 设备管理
    - RPC处理
    - 属性更新处理
    """
    
    def __init__(self, gateway, config, connector_type):
        """
        初始化连接器
        
        Args:
            gateway: 网关实例
            config: 连接器配置
            connector_type: 连接器类型
        """
        super().__init__()
        self._gateway = gateway
        self._config = config
        self._connector_type = connector_type
        
        # 连接器状态
        self._connected = False
        self._stopped = False
        
        # 从配置中读取参数
        self._name = config.get('name', 'Example Connector')
        self._id = config.get('id', 'example_connector_001')
        
        # 读取设备配置
        self._devices = config.get('devices', [])
        
        # 数据采集线程
        self._data_thread = None
        self._poll_interval = config.get('pollInterval', 5)  # 默认5秒
        
        log.info("ExampleConnector '%s' initialized with %d devices", 
                 self._name, len(self._devices))
    
    def open(self):
        """打开连接器"""
        log.info("Opening ExampleConnector '%s'", self._name)
        
        self._stopped = False
        self._connected = True
        
        # 注册设备到网关
        for device in self._devices:
            device_name = device.get('deviceName', 'Unknown')
            device_type = device.get('deviceType', 'default')
            
            self._gateway.add_device(
                device_name=device_name,
                content={
                    'deviceName': device_name,
                    'deviceType': device_type
                },
                device_type=device_type
            )
            
            log.info("Device '%s' registered", device_name)
        
        # 启动数据采集线程
        self._data_thread = Thread(target=self._poll_data, daemon=True, 
                                   name=f"{self._name} Data Thread")
        self._data_thread.start()
        
        log.info("ExampleConnector '%s' opened successfully", self._name)
    
    def close(self):
        """关闭连接器"""
        log.info("Closing ExampleConnector '%s'", self._name)
        
        self._stopped = True
        self._connected = False
        
        # 等待数据线程结束
        if self._data_thread and self._data_thread.is_alive():
            self._data_thread.join(timeout=5)
        
        log.info("ExampleConnector '%s' closed", self._name)
    
    def get_id(self):
        """获取连接器ID"""
        return self._id
    
    def get_name(self):
        """获取连接器名称"""
        return self._name
    
    def get_type(self):
        """获取连接器类型"""
        return self._connector_type
    
    def get_config(self):
        """获取连接器配置"""
        return self._config
    
    def is_connected(self):
        """检查是否已连接"""
        return self._connected
    
    def is_stopped(self):
        """检查是否已停止"""
        return self._stopped
    
    def on_attributes_update(self, content):
        """
        处理属性更新
        
        Args:
            content: 属性更新内容
        """
        log.info("Received attributes update: %s", content)
        
        try:
            device_name = content.get('device')
            attributes = content.get('data', {})
            
            log.info("Updating attributes for device '%s': %s", 
                    device_name, attributes)
            
            # 在这里实现属性更新逻辑
            # 例如：将属性写入设备
            
        except Exception as e:
            log.error("Error processing attributes update: %s", e, exc_info=True)
    
    def server_side_rpc_handler(self, content):
        """
        处理服务端RPC请求
        
        Args:
            content: RPC请求内容
        """
        log.info("Received RPC request: %s", content)
        
        try:
            device_name = content.get('device')
            method = content.get('data', {}).get('method')
            params = content.get('data', {}).get('params', {})
            
            log.info("Processing RPC for device '%s', method '%s', params: %s",
                    device_name, method, params)
            
            # 处理不同的RPC方法
            if method == 'getValue':
                # 返回一个模拟值
                response = {
                    'value': random.randint(0, 100),
                    'timestamp': int(time.time() * 1000)
                }
            elif method == 'setValue':
                # 设置值
                value = params.get('value')
                log.info("Setting value to %s for device '%s'", value, device_name)
                response = {'success': True, 'value': value}
            else:
                response = {'error': f'Unknown method: {method}'}
            
            # 发送RPC响应
            self._gateway.send_rpc_reply(
                device=device_name,
                req_id=content.get('data', {}).get('id'),
                content=response
            )
            
        except Exception as e:
            log.error("Error processing RPC: %s", e, exc_info=True)
    
    def _poll_data(self):
        """数据采集循环"""
        log.info("Data polling started (interval: %d seconds)", self._poll_interval)
        
        while not self._stopped:
            try:
                # 为每个设备生成并发送数据
                for device in self._devices:
                    if self._stopped:
                        break
                    
                    device_name = device.get('deviceName', 'Unknown')
                    
                    # 生成模拟遥测数据
                    telemetry = {
                        'temperature': round(random.uniform(20.0, 30.0), 2),
                        'humidity': round(random.uniform(40.0, 80.0), 2),
                        'pressure': round(random.uniform(990.0, 1020.0), 2),
                        'status': random.choice(['online', 'active', 'idle'])
                    }
                    
                    # 发送遥测数据到网关
                    self._gateway.send_to_storage(
                        self._name,
                        self._id,
                        {
                            'deviceName': device_name,
                            'deviceType': device.get('deviceType', 'default'),
                            'telemetry': [{
                                'ts': int(time.time() * 1000),
                                'values': telemetry
                            }],
                            CONNECTOR_PARAMETER: self
                        }
                    )
                    
                    log.debug("Sent telemetry for device '%s': %s", 
                             device_name, telemetry)
                
                # 等待下一次采集
                time.sleep(self._poll_interval)
                
            except Exception as e:
                log.error("Error in data polling: %s", e, exc_info=True)
                time.sleep(self._poll_interval)
        
        log.info("Data polling stopped")
