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
插件管理器模块
负责插件的安装、卸载、启用、禁用等生命周期管理
"""

import json
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from time import time
from typing import Dict, List, Optional, Tuple

from packaging import version

from thingsboard_gateway.gateway.plugin_system.plugin_spec import PluginMetadata, PluginSpec, PluginType
from thingsboard_gateway.tb_utility.tb_logger import TbLogger

logging.setLoggerClass(TbLogger)
log = logging.getLogger("plugin_manager")


class PluginManager:
    """
    插件管理器
    
    负责插件的完整生命周期管理：
    - 安装和卸载插件
    - 启用和禁用插件
    - 验证插件兼容性
    - 管理插件依赖
    """
    
    PLUGIN_MANIFEST = "plugin.json"
    PLUGINS_REGISTRY = "plugins_registry.json"
    
    def __init__(self, plugins_dir: str, config_dir: str):
        """
        初始化插件管理器
        
        Args:
            plugins_dir: 插件安装目录
            config_dir: 配置文件目录
        """
        self.plugins_dir = Path(plugins_dir)
        self.config_dir = Path(config_dir)
        self.registry_file = self.config_dir / self.PLUGINS_REGISTRY
        
        # 创建必要的目录
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # 加载插件注册表
        self.registry: Dict[str, PluginSpec] = self._load_registry()
        
        log.info("Plugin manager initialized. Plugins dir: %s", self.plugins_dir)
    
    def _load_registry(self) -> Dict[str, PluginSpec]:
        """加载插件注册表"""
        if not self.registry_file.exists():
            return {}
        
        try:
            with open(self.registry_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return {name: PluginSpec.from_dict(spec) for name, spec in data.items()}
        except Exception as e:
            log.error("Failed to load plugin registry: %s", e)
            return {}
    
    def _save_registry(self):
        """保存插件注册表"""
        try:
            data = {name: spec.to_dict() for name, spec in self.registry.items()}
            with open(self.registry_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            log.error("Failed to save plugin registry: %s", e)
    
    def install_plugin(self, plugin_package: str, force: bool = False) -> Tuple[bool, str]:
        """
        安装插件
        
        Args:
            plugin_package: 插件包路径（.zip文件）
            force: 是否强制安装（覆盖已存在的插件）
        
        Returns:
            (成功标志, 消息)
        """
        try:
            # 1. 验证插件包
            if not os.path.exists(plugin_package):
                return False, f"Plugin package not found: {plugin_package}"
            
            if not zipfile.is_zipfile(plugin_package):
                return False, "Invalid plugin package: not a zip file"
            
            # 2. 创建临时目录解压插件包
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # 解压插件包
                with zipfile.ZipFile(plugin_package, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # 3. 读取并验证插件元数据
                manifest_file = temp_path / self.PLUGIN_MANIFEST
                if not manifest_file.exists():
                    return False, f"Missing {self.PLUGIN_MANIFEST} in plugin package"
                
                with open(manifest_file, 'r', encoding='utf-8') as f:
                    metadata_dict = json.load(f)
                
                metadata = PluginMetadata.from_dict(metadata_dict)
                
                # 4. 验证插件
                valid, msg = self._validate_plugin(metadata, force)
                if not valid:
                    return False, msg
                
                # 5. 安装插件依赖
                if metadata.dependencies:
                    log.info("Installing dependencies for plugin %s", metadata.name)
                    success, msg = self._install_dependencies(metadata.dependencies)
                    if not success:
                        return False, f"Failed to install dependencies: {msg}"
                
                # 6. 复制插件文件到插件目录
                plugin_install_dir = self.plugins_dir / metadata.connector_type
                
                # 如果插件已存在且不强制安装，则失败
                if plugin_install_dir.exists() and not force:
                    return False, f"Plugin {metadata.name} already installed. Use force=True to overwrite."
                
                # 删除旧版本（如果存在）
                if plugin_install_dir.exists():
                    shutil.rmtree(plugin_install_dir)
                
                # 复制插件文件
                shutil.copytree(temp_path, plugin_install_dir)
                
                # 7. 注册插件
                plugin_spec = PluginSpec(
                    metadata=metadata,
                    install_path=str(plugin_install_dir),
                    enabled=True,
                    install_time=time()
                )
                
                self.registry[metadata.name] = plugin_spec
                self._save_registry()
                
                log.info("Plugin %s (v%s) installed successfully", metadata.name, metadata.version)
                return True, f"Plugin {metadata.name} installed successfully"
        
        except Exception as e:
            log.error("Failed to install plugin: %s", e, exc_info=True)
            return False, f"Installation failed: {str(e)}"
    
    def uninstall_plugin(self, plugin_name: str) -> Tuple[bool, str]:
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
        
        Returns:
            (成功标志, 消息)
        """
        try:
            # 1. 检查插件是否存在
            if plugin_name not in self.registry:
                return False, f"Plugin {plugin_name} not found"
            
            plugin_spec = self.registry[plugin_name]
            
            # 2. 删除插件文件
            install_path = Path(plugin_spec.install_path)
            if install_path.exists():
                shutil.rmtree(install_path)
            
            # 3. 从注册表中移除
            del self.registry[plugin_name]
            self._save_registry()
            
            log.info("Plugin %s uninstalled successfully", plugin_name)
            return True, f"Plugin {plugin_name} uninstalled successfully"
        
        except Exception as e:
            log.error("Failed to uninstall plugin %s: %s", plugin_name, e)
            return False, f"Uninstallation failed: {str(e)}"
    
    def enable_plugin(self, plugin_name: str) -> Tuple[bool, str]:
        """启用插件"""
        if plugin_name not in self.registry:
            return False, f"Plugin {plugin_name} not found"
        
        self.registry[plugin_name].enabled = True
        self._save_registry()
        
        log.info("Plugin %s enabled", plugin_name)
        return True, f"Plugin {plugin_name} enabled"
    
    def disable_plugin(self, plugin_name: str) -> Tuple[bool, str]:
        """禁用插件"""
        if plugin_name not in self.registry:
            return False, f"Plugin {plugin_name} not found"
        
        self.registry[plugin_name].enabled = False
        self._save_registry()
        
        log.info("Plugin %s disabled", plugin_name)
        return True, f"Plugin {plugin_name} disabled"
    
    def list_plugins(self, enabled_only: bool = False) -> List[Dict]:
        """
        列出所有插件
        
        Args:
            enabled_only: 是否只列出启用的插件
        
        Returns:
            插件列表
        """
        plugins = []
        for name, spec in self.registry.items():
            if enabled_only and not spec.enabled:
                continue
            
            plugins.append({
                'name': name,
                'version': spec.metadata.version,
                'type': spec.metadata.plugin_type.value,
                'connector_type': spec.metadata.connector_type,
                'display_name': spec.metadata.display_name,
                'description': spec.metadata.description,
                'enabled': spec.enabled,
                'install_path': spec.install_path,
                'install_time': spec.install_time
            })
        
        return plugins
    
    def get_plugin(self, plugin_name: str) -> Optional[PluginSpec]:
        """获取插件信息"""
        return self.registry.get(plugin_name)
    
    def get_enabled_plugin_paths(self) -> List[str]:
        """获取所有启用插件的安装路径"""
        return [spec.install_path for spec in self.registry.values() if spec.enabled]
    
    def _validate_plugin(self, metadata: PluginMetadata, force: bool) -> Tuple[bool, str]:
        """
        验证插件
        
        Args:
            metadata: 插件元数据
            force: 是否强制安装
        
        Returns:
            (是否有效, 错误消息)
        """
        # 1. 检查必需字段
        if not metadata.name:
            return False, "Plugin name is required"
        
        if not metadata.version:
            return False, "Plugin version is required"
        
        if not metadata.connector_type:
            return False, "Connector type is required"
        
        # 2. 检查版本格式
        try:
            version.parse(metadata.version)
        except Exception:
            return False, f"Invalid version format: {metadata.version}"
        
        # 3. 检查是否已安装
        if not force and metadata.name in self.registry:
            installed_version = self.registry[metadata.name].metadata.version
            return False, f"Plugin {metadata.name} v{installed_version} is already installed"
        
        # 4. 检查Python版本兼容性
        try:
            current_python = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            # 这里可以添加更详细的版本检查
            log.info("Current Python version: %s, Required: %s", current_python, metadata.python_requires)
        except Exception as e:
            log.warning("Failed to check Python version compatibility: %s", e)
        
        return True, ""
    
    def _install_dependencies(self, dependencies: List[str]) -> Tuple[bool, str]:
        """
        安装插件依赖
        
        Args:
            dependencies: 依赖包列表
        
        Returns:
            (成功标志, 消息)
        """
        try:
            for dep in dependencies:
                log.info("Installing dependency: %s", dep)
                result = subprocess.run(
                    [sys.executable, "-m", "pip", "install", dep],
                    capture_output=True,
                    text=True,
                    timeout=300
                )
                
                if result.returncode != 0:
                    return False, f"Failed to install {dep}: {result.stderr}"
            
            return True, "All dependencies installed"
        
        except subprocess.TimeoutExpired:
            return False, "Dependency installation timeout"
        except Exception as e:
            return False, f"Dependency installation error: {str(e)}"
    
    def create_plugin_package(self, source_dir: str, output_file: str) -> Tuple[bool, str]:
        """
        创建插件包
        
        Args:
            source_dir: 源代码目录
            output_file: 输出的zip文件路径
        
        Returns:
            (成功标志, 消息)
        """
        try:
            source_path = Path(source_dir)
            
            # 检查plugin.json是否存在
            manifest_file = source_path / self.PLUGIN_MANIFEST
            if not manifest_file.exists():
                return False, f"Missing {self.PLUGIN_MANIFEST} in source directory"
            
            # 创建zip文件
            with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file_path in source_path.rglob('*'):
                    if file_path.is_file():
                        # 排除某些文件
                        if file_path.name.endswith(('.pyc', '.pyo', '.pyd', '__pycache__')):
                            continue
                        
                        arcname = file_path.relative_to(source_path)
                        zipf.write(file_path, arcname)
            
            log.info("Plugin package created: %s", output_file)
            return True, f"Plugin package created: {output_file}"
        
        except Exception as e:
            log.error("Failed to create plugin package: %s", e)
            return False, f"Failed to create package: {str(e)}"
