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
网关插件集成模块
提供插件系统与网关服务的集成功能
"""

import logging
import os
from pathlib import Path
from threading import Thread
from typing import Optional

from thingsboard_gateway.gateway.plugin_system.plugin_manager import PluginManager
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader
from thingsboard_gateway.tb_utility.tb_logger import TbLogger

logging.setLoggerClass(TbLogger)
log = logging.getLogger("plugin_integration")


class GatewayPluginIntegration:
    """
    网关插件集成类
    
    负责将插件系统集成到ThingsBoard网关服务中
    """
    
    def __init__(self, config_dir: str, enable_api: bool = True, api_host: str = "0.0.0.0", api_port: int = 9001):
        """
        初始化插件集成
        
        Args:
            config_dir: 配置目录
            enable_api: 是否启用REST API
            api_host: API监听地址
            api_port: API监听端口
        """
        self.config_dir = Path(config_dir)
        self.enable_api = enable_api
        
        # 设置插件目录
        self.plugins_dir = self.config_dir / "plugins"
        self.plugins_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化插件管理器
        self.plugin_manager = PluginManager(
            plugins_dir=str(self.plugins_dir),
            config_dir=str(self.config_dir)
        )
        
        # 初始化API服务器（可选）
        self.api_server = None
        self.api_thread = None
        
        if self.enable_api:
            try:
                from thingsboard_gateway.gateway.plugin_system.plugin_api import PluginAPI
                self.api_server = PluginAPI(
                    plugin_manager=self.plugin_manager,
                    host=api_host,
                    port=api_port
                )
            except ImportError as e:
                log.warning("Plugin API is disabled due to missing dependencies: %s", e)
                self.enable_api = False
        
        log.info("Gateway plugin integration initialized")
    
    def start(self):
        """启动插件系统"""
        # 1. 加载已安装的插件路径到模块加载器
        self._load_plugin_paths()
        
        # 2. 启动API服务器（如果启用）
        if self.enable_api and self.api_server:
            self._start_api_server()
        
        log.info("Plugin system started")
    
    def stop(self):
        """停止插件系统"""
        # 停止API服务器
        # 注意：Flask的run()方法不易停止，在生产环境中应使用WSGI服务器
        log.info("Plugin system stopped")
    
    def _load_plugin_paths(self):
        """加载插件路径到模块加载器"""
        enabled_plugins = self.plugin_manager.list_plugins(enabled_only=True)
        
        for plugin_info in enabled_plugins:
            install_path = plugin_info['install_path']
            if os.path.exists(install_path):
                # 将插件路径添加到模块加载器
                TBModuleLoader.add_plugin_path(install_path)
                log.info("Loaded plugin path: %s (type: %s)", 
                         install_path, plugin_info['connector_type'])
    
    def _start_api_server(self):
        """启动API服务器（在单独的线程中）"""
        def run_server():
            try:
                self.api_server.run(debug=False, threaded=True)
            except Exception as e:
                log.error("Plugin API server error: %s", e, exc_info=True)
        
        self.api_thread = Thread(target=run_server, daemon=True, name="PluginAPIServer")
        self.api_thread.start()
        log.info("Plugin API server started in background thread")
    
    def reload_plugins(self):
        """重新加载插件（在插件安装/卸载后调用）"""
        # 清除旧的插件路径
        for plugin_info in self.plugin_manager.list_plugins():
            install_path = plugin_info['install_path']
            TBModuleLoader.remove_plugin_path(install_path)
        
        # 重新加载启用的插件
        self._load_plugin_paths()
        
        log.info("Plugins reloaded")
    
    def install_plugin_from_file(self, plugin_file: str, force: bool = False):
        """
        从文件安装插件
        
        Args:
            plugin_file: 插件包文件路径
            force: 是否强制安装
        
        Returns:
            (成功标志, 消息)
        """
        success, message = self.plugin_manager.install_plugin(plugin_file, force=force)
        
        if success:
            # 重新加载插件路径
            self.reload_plugins()
        
        return success, message
    
    def uninstall_plugin(self, plugin_name: str):
        """
        卸载插件
        
        Args:
            plugin_name: 插件名称
        
        Returns:
            (成功标志, 消息)
        """
        success, message = self.plugin_manager.uninstall_plugin(plugin_name)
        
        if success:
            # 重新加载插件路径
            self.reload_plugins()
        
        return success, message


def create_plugin_integration(gateway_service) -> Optional[GatewayPluginIntegration]:
    """
    为网关服务创建插件集成
    
    Args:
        gateway_service: TBGatewayService实例
    
    Returns:
        GatewayPluginIntegration实例或None
    """
    try:
        # 从网关配置中读取插件系统配置
        plugin_config = gateway_service.config.get('plugins', {})
        
        if not plugin_config.get('enabled', True):
            log.info("Plugin system is disabled in configuration")
            return None
        
        config_dir = gateway_service._config_dir
        
        # 创建插件集成
        integration = GatewayPluginIntegration(
            config_dir=config_dir,
            enable_api=plugin_config.get('enable_api', True),
            api_host=plugin_config.get('api_host', '0.0.0.0'),
            api_port=plugin_config.get('api_port', 9001)
        )
        
        # 启动插件系统
        integration.start()
        
        return integration
    
    except Exception as e:
        log.error("Failed to create plugin integration: %s", e, exc_info=True)
        return None
