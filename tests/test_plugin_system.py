#!/usr/bin/env python3
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
插件系统测试
"""

import json
import os
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch, Mock

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from thingsboard_gateway.gateway.plugin_system.plugin_manager import PluginManager
from thingsboard_gateway.gateway.plugin_system.plugin_api import PluginAPI, FLASK_AVAILABLE
from thingsboard_gateway.gateway.plugin_system.plugin_spec import PluginMetadata, PluginType


class TestPluginSystem(unittest.TestCase):
    """插件系统测试用例"""
    
    def setUp(self):
        """测试准备"""
        # 创建临时目录
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = os.path.join(self.temp_dir, "plugins")
        self.config_dir = os.path.join(self.temp_dir, "config")
        
        os.makedirs(self.plugins_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)
        
        # 创建插件管理器
        self.plugin_manager = PluginManager(
            plugins_dir=self.plugins_dir,
            config_dir=self.config_dir
        )
    
    def tearDown(self):
        """测试清理"""
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)
    
    def create_test_plugin_package(self, connector_type="test"):
        """创建测试插件包"""
        # 创建临时插件目录
        plugin_src = os.path.join(self.temp_dir, f"{connector_type}_plugin_src")
        os.makedirs(plugin_src, exist_ok=True)
        
        # 创建plugin.json
        manifest = {
            "name": f"{connector_type}_connector_plugin",
            "version": "1.0.0",
            "plugin_type": "connector",
            "connector_type": connector_type,
            "display_name": f"{connector_type.upper()} Connector",
            "description": "Test connector",
            "author": "Test",
            "license": "Apache-2.0",
            "python_requires": ">=3.7",
            "dependencies": [],
            "entry_point": f"{connector_type.capitalize()}Connector",
            "module_name": f"{connector_type}_connector",
            "gateway_version": ">=3.0"
        }
        
        with open(os.path.join(plugin_src, "plugin.json"), 'w') as f:
            json.dump(manifest, f, indent=2)
        
        # 创建简单的连接器文件
        connector_code = f'''
from thingsboard_gateway.connectors.connector import Connector

class {connector_type.capitalize()}Connector(Connector):
    def __init__(self, gateway, config, connector_type):
        super().__init__()
        self._gateway = gateway
        self._config = config
        self._connector_type = connector_type
    
    def open(self):
        pass
    
    def close(self):
        pass
    
    def get_id(self):
        return "test_id"
    
    def get_name(self):
        return "test_name"
    
    def get_type(self):
        return self._connector_type
    
    def get_config(self):
        return self._config
    
    def is_connected(self):
        return True
    
    def is_stopped(self):
        return False
    
    def on_attributes_update(self, content):
        pass
    
    def server_side_rpc_handler(self, content):
        pass
'''
        
        with open(os.path.join(plugin_src, f"{connector_type}_connector.py"), 'w') as f:
            f.write(connector_code)
        
        # 打包为zip
        plugin_package = os.path.join(self.temp_dir, f"{connector_type}_plugin.zip")
        with zipfile.ZipFile(plugin_package, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(plugin_src):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, plugin_src)
                    zipf.write(file_path, arcname)
        
        return plugin_package
    
    def test_plugin_metadata_creation(self):
        """测试插件元数据创建"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
            connector_type="test"
        )
        
        self.assertEqual(metadata.name, "test_plugin")
        self.assertEqual(metadata.version, "1.0.0")
        self.assertEqual(metadata.connector_type, "test")
        self.assertEqual(metadata.plugin_type, PluginType.CONNECTOR)
    
    def test_plugin_metadata_to_dict(self):
        """测试插件元数据序列化"""
        metadata = PluginMetadata(
            name="test_plugin",
            version="1.0.0",
            plugin_type=PluginType.CONNECTOR,
            connector_type="test"
        )
        
        data = metadata.to_dict()
        
        self.assertIsInstance(data, dict)
        self.assertEqual(data['name'], "test_plugin")
        self.assertEqual(data['plugin_type'], "connector")
    
    def test_plugin_metadata_from_dict(self):
        """测试插件元数据反序列化"""
        data = {
            "name": "test_plugin",
            "version": "1.0.0",
            "plugin_type": "connector",
            "connector_type": "test"
        }
        
        metadata = PluginMetadata.from_dict(data)
        
        self.assertEqual(metadata.name, "test_plugin")
        self.assertEqual(metadata.version, "1.0.0")
    
    def test_plugin_install(self):
        """测试插件安装"""
        # 创建测试插件包
        plugin_package = self.create_test_plugin_package("testconn")
        
        # 安装插件
        success, message = self.plugin_manager.install_plugin(plugin_package)
        
        self.assertTrue(success, f"Plugin installation failed: {message}")
        
        # 验证插件已注册
        plugins = self.plugin_manager.list_plugins()
        self.assertEqual(len(plugins), 1)
        self.assertEqual(plugins[0]['connector_type'], "testconn")
    
    def test_plugin_list(self):
        """测试插件列表"""
        # 安装两个插件
        plugin1 = self.create_test_plugin_package("plugin1")
        plugin2 = self.create_test_plugin_package("plugin2")
        
        self.plugin_manager.install_plugin(plugin1)
        self.plugin_manager.install_plugin(plugin2)
        
        # 列出所有插件
        plugins = self.plugin_manager.list_plugins()
        self.assertEqual(len(plugins), 2)
        
        # 禁用一个插件
        self.plugin_manager.disable_plugin("plugin1_connector_plugin")
        
        # 只列出启用的插件
        enabled_plugins = self.plugin_manager.list_plugins(enabled_only=True)
        self.assertEqual(len(enabled_plugins), 1)
        self.assertEqual(enabled_plugins[0]['connector_type'], "plugin2")
    
    def test_plugin_enable_disable(self):
        """测试插件启用/禁用"""
        plugin_package = self.create_test_plugin_package("testplugin")
        self.plugin_manager.install_plugin(plugin_package)
        
        plugin_name = "testplugin_connector_plugin"
        
        # 禁用插件
        success, message = self.plugin_manager.disable_plugin(plugin_name)
        self.assertTrue(success)
        
        plugin = self.plugin_manager.get_plugin(plugin_name)
        self.assertFalse(plugin.enabled)
        
        # 启用插件
        success, message = self.plugin_manager.enable_plugin(plugin_name)
        self.assertTrue(success)
        
        plugin = self.plugin_manager.get_plugin(plugin_name)
        self.assertTrue(plugin.enabled)
    
    def test_plugin_uninstall(self):
        """测试插件卸载"""
        plugin_package = self.create_test_plugin_package("uninstalltest")
        self.plugin_manager.install_plugin(plugin_package)
        
        plugin_name = "uninstalltest_connector_plugin"
        
        # 验证插件已安装
        self.assertIsNotNone(self.plugin_manager.get_plugin(plugin_name))
        
        # 卸载插件
        success, message = self.plugin_manager.uninstall_plugin(plugin_name)
        self.assertTrue(success)
        
        # 验证插件已卸载
        self.assertIsNone(self.plugin_manager.get_plugin(plugin_name))
    
    def test_plugin_force_install(self):
        """测试强制安装插件"""
        plugin_package = self.create_test_plugin_package("forcetest")
        
        # 首次安装
        success1, _ = self.plugin_manager.install_plugin(plugin_package)
        self.assertTrue(success1)
        
        # 再次安装（不强制）应该失败
        success2, message2 = self.plugin_manager.install_plugin(plugin_package, force=False)
        self.assertFalse(success2)
        self.assertIn("already installed", message2)
        
        # 强制安装应该成功
        success3, _ = self.plugin_manager.install_plugin(plugin_package, force=True)
        self.assertTrue(success3)


@unittest.skipUnless(FLASK_AVAILABLE, "Flask is required for PluginAPI auth tests")
class TestPluginApiAuth(unittest.TestCase):
    """插件API认证测试"""

    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.plugins_dir = os.path.join(self.temp_dir, "plugins")
        self.config_dir = os.path.join(self.temp_dir, "config")

        os.makedirs(self.plugins_dir, exist_ok=True)
        os.makedirs(self.config_dir, exist_ok=True)

        self.plugin_manager = PluginManager(
            plugins_dir=self.plugins_dir,
            config_dir=self.config_dir
        )

    def tearDown(self):
        import shutil
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_static_token_auth_blocks_unauthorized_requests(self):
        api = PluginAPI(
            plugin_manager=self.plugin_manager,
            auth_config={
                "type": "static_token",
                "tokens": ["secret-token"]
            }
        )

        client = api.get_app().test_client()

        unauthorized = client.get('/api/plugins')
        self.assertEqual(unauthorized.status_code, 401)

        authorized = client.get('/api/plugins', headers={"Authorization": "Bearer secret-token"})
        self.assertEqual(authorized.status_code, 200)

    @patch('thingsboard_gateway.gateway.plugin_system.plugin_api.requests.get')
    def test_thingsboard_jwt_auth_validates_authority(self, mock_get):
        response = Mock()
        response.status_code = 200
        response.json.return_value = {"authority": "TENANT_ADMIN"}
        mock_get.return_value = response

        api = PluginAPI(
            plugin_manager=self.plugin_manager,
            auth_config={
                "type": "thingsboard_jwt",
                "validation_url": "http://tb.local/api/auth/user",
                "allowed_authorities": ["TENANT_ADMIN"]
            }
        )

        client = api.get_app().test_client()
        result = client.get('/api/plugins', headers={"Authorization": "Bearer jwt-token"})

        self.assertEqual(result.status_code, 200)
        mock_get.assert_called_once()


def run_tests():
    """运行测试"""
    print("运行插件系统测试...")
    print("=" * 70)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestPluginSystem)
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("=" * 70)
    if result.wasSuccessful():
        print("✓ 所有测试通过！")
        return 0
    else:
        print("✗ 部分测试失败")
        return 1


if __name__ == '__main__':
    sys.exit(run_tests())
