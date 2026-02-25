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
插件规范模块
定义插件的元数据结构和验证规则
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional
from enum import Enum


class PluginType(Enum):
    """插件类型枚举"""
    CONNECTOR = "connector"
    CONVERTER = "converter"
    EXTENSION = "extension"


@dataclass
class PluginMetadata:
    """
    插件元数据类
    
    定义插件包的基本信息和依赖关系
    """
    # 必需字段
    name: str                          # 插件名称（唯一标识符）
    version: str                       # 版本号（遵循语义化版本）
    plugin_type: PluginType            # 插件类型
    connector_type: str                # 连接器类型（如opcua, modbus等）
    
    # 可选字段
    display_name: str = ""             # 显示名称
    description: str = ""              # 插件描述
    author: str = ""                   # 作者
    license: str = "Apache-2.0"        # 许可证
    homepage: str = ""                 # 主页URL
    
    # 依赖信息
    python_requires: str = ">=3.7"     # Python版本要求
    dependencies: List[str] = field(default_factory=list)  # Python包依赖
    
    # 插件入口点
    entry_point: str = ""              # 主类名称（如OpcuaConnector）
    module_name: str = ""              # 模块文件名（如opcua_connector）
    
    # 配置
    config_template: Optional[Dict] = None  # 配置模板
    
    # 兼容性
    gateway_version: str = ">=3.0"     # 网关版本要求
    
    def __post_init__(self):
        """初始化后验证"""
        if isinstance(self.plugin_type, str):
            self.plugin_type = PluginType(self.plugin_type)
        
        if not self.display_name:
            self.display_name = self.name
        
        if not self.module_name:
            self.module_name = f"{self.connector_type}_connector"
        
        if not self.entry_point:
            # 自动生成入口点类名
            parts = self.connector_type.split('_')
            self.entry_point = ''.join(p.capitalize() for p in parts) + 'Connector'
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'name': self.name,
            'version': self.version,
            'plugin_type': self.plugin_type.value,
            'connector_type': self.connector_type,
            'display_name': self.display_name,
            'description': self.description,
            'author': self.author,
            'license': self.license,
            'homepage': self.homepage,
            'python_requires': self.python_requires,
            'dependencies': self.dependencies,
            'entry_point': self.entry_point,
            'module_name': self.module_name,
            'config_template': self.config_template,
            'gateway_version': self.gateway_version
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PluginMetadata':
        """从字典创建实例"""
        return cls(
            name=data['name'],
            version=data['version'],
            plugin_type=data['plugin_type'],
            connector_type=data['connector_type'],
            display_name=data.get('display_name', ''),
            description=data.get('description', ''),
            author=data.get('author', ''),
            license=data.get('license', 'Apache-2.0'),
            homepage=data.get('homepage', ''),
            python_requires=data.get('python_requires', '>=3.7'),
            dependencies=data.get('dependencies', []),
            entry_point=data.get('entry_point', ''),
            module_name=data.get('module_name', ''),
            config_template=data.get('config_template'),
            gateway_version=data.get('gateway_version', '>=3.0')
        )


@dataclass
class PluginSpec:
    """
    插件规范类
    
    表示一个已安装的插件
    """
    metadata: PluginMetadata           # 插件元数据
    install_path: str                  # 安装路径
    enabled: bool = True               # 是否启用
    install_time: Optional[float] = None  # 安装时间戳
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'metadata': self.metadata.to_dict(),
            'install_path': self.install_path,
            'enabled': self.enabled,
            'install_time': self.install_time
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'PluginSpec':
        """从字典创建实例"""
        return cls(
            metadata=PluginMetadata.from_dict(data['metadata']),
            install_path=data['install_path'],
            enabled=data.get('enabled', True),
            install_time=data.get('install_time')
        )
