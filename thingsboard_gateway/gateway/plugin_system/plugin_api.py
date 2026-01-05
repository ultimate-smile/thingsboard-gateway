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
插件REST API模块
提供HTTP接口用于管理插件
"""

import json
import logging
import os
import tempfile
from pathlib import Path
from typing import Optional

try:
    from flask import Flask, request, jsonify, send_file
    from werkzeug.utils import secure_filename
    FLASK_AVAILABLE = True
except ImportError:
    FLASK_AVAILABLE = False
    Flask = None

from thingsboard_gateway.gateway.plugin_system.plugin_manager import PluginManager
from thingsboard_gateway.tb_utility.tb_logger import TbLogger

logging.setLoggerClass(TbLogger)
log = logging.getLogger("plugin_api")


class PluginAPI:
    """
    插件API类
    
    提供RESTful API用于插件管理
    """
    
    def __init__(self, plugin_manager: PluginManager, host: str = "0.0.0.0", port: int = 9001):
        """
        初始化插件API
        
        Args:
            plugin_manager: 插件管理器实例
            host: 监听地址
            port: 监听端口
        """
        if not FLASK_AVAILABLE:
            raise ImportError("Flask is required for Plugin API. Install it with: pip install flask")
        
        self.plugin_manager = plugin_manager
        self.host = host
        self.port = port
        self.app = Flask(__name__)
        
        # 配置上传文件夹
        self.upload_folder = Path(tempfile.gettempdir()) / "gateway_plugins_upload"
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.app.config['UPLOAD_FOLDER'] = str(self.upload_folder)
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB
        
        self._register_routes()
        
        log.info("Plugin API initialized on %s:%s", host, port)
    
    def _register_routes(self):
        """注册API路由"""
        
        @self.app.route('/api/plugins', methods=['GET'])
        def list_plugins():
            """列出所有插件"""
            try:
                enabled_only = request.args.get('enabled', 'false').lower() == 'true'
                plugins = self.plugin_manager.list_plugins(enabled_only=enabled_only)
                return jsonify({
                    'success': True,
                    'plugins': plugins,
                    'count': len(plugins)
                })
            except Exception as e:
                log.error("Failed to list plugins: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/plugins/<plugin_name>', methods=['GET'])
        def get_plugin(plugin_name):
            """获取插件详细信息"""
            try:
                plugin = self.plugin_manager.get_plugin(plugin_name)
                if plugin is None:
                    return jsonify({
                        'success': False,
                        'error': f'Plugin {plugin_name} not found'
                    }), 404
                
                return jsonify({
                    'success': True,
                    'plugin': plugin.to_dict()
                })
            except Exception as e:
                log.error("Failed to get plugin %s: %s", plugin_name, e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/plugins/upload', methods=['POST'])
        def upload_plugin():
            """上传并安装插件"""
            try:
                # 检查文件
                if 'file' not in request.files:
                    return jsonify({
                        'success': False,
                        'error': 'No file provided'
                    }), 400
                
                file = request.files['file']
                if file.filename == '':
                    return jsonify({
                        'success': False,
                        'error': 'No file selected'
                    }), 400
                
                if not file.filename.endswith('.zip'):
                    return jsonify({
                        'success': False,
                        'error': 'Only .zip files are allowed'
                    }), 400
                
                # 保存上传的文件
                filename = secure_filename(file.filename)
                file_path = os.path.join(self.app.config['UPLOAD_FOLDER'], filename)
                file.save(file_path)
                
                # 获取安装选项
                force = request.form.get('force', 'false').lower() == 'true'
                
                # 安装插件
                success, message = self.plugin_manager.install_plugin(file_path, force=force)
                
                # 删除临时文件
                try:
                    os.remove(file_path)
                except:
                    pass
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': message
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': message
                    }), 400
            
            except Exception as e:
                log.error("Failed to upload plugin: %s", e, exc_info=True)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/plugins/<plugin_name>', methods=['DELETE'])
        def uninstall_plugin(plugin_name):
            """卸载插件"""
            try:
                success, message = self.plugin_manager.uninstall_plugin(plugin_name)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': message
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': message
                    }), 400
            
            except Exception as e:
                log.error("Failed to uninstall plugin %s: %s", plugin_name, e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/plugins/<plugin_name>/enable', methods=['POST'])
        def enable_plugin(plugin_name):
            """启用插件"""
            try:
                success, message = self.plugin_manager.enable_plugin(plugin_name)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': message
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': message
                    }), 400
            
            except Exception as e:
                log.error("Failed to enable plugin %s: %s", plugin_name, e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/plugins/<plugin_name>/disable', methods=['POST'])
        def disable_plugin(plugin_name):
            """禁用插件"""
            try:
                success, message = self.plugin_manager.disable_plugin(plugin_name)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': message
                    })
                else:
                    return jsonify({
                        'success': False,
                        'error': message
                    }), 400
            
            except Exception as e:
                log.error("Failed to disable plugin %s: %s", plugin_name, e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/plugins/health', methods=['GET'])
        def health_check():
            """健康检查"""
            return jsonify({
                'success': True,
                'status': 'healthy',
                'plugin_count': len(self.plugin_manager.registry)
            })
    
    def run(self, debug: bool = False, threaded: bool = True):
        """
        启动API服务器
        
        Args:
            debug: 是否启用调试模式
            threaded: 是否启用多线程
        """
        log.info("Starting Plugin API server on %s:%s", self.host, self.port)
        self.app.run(host=self.host, port=self.port, debug=debug, threaded=threaded)
    
    def get_app(self):
        """获取Flask应用实例（用于集成到其他服务器）"""
        return self.app
