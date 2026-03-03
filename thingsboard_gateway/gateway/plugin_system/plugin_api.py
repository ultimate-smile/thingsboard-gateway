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
import hmac
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

import requests

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
    
    def __init__(self,
                 plugin_manager: PluginManager,
                 host: str = "0.0.0.0",
                 port: int = 9001,
                 auth_config: Optional[Dict] = None):
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
        self.auth_config = auth_config or {}
        self._auth_cache: Dict[str, Tuple[float, Dict]] = {}
        
        # 配置上传文件夹
        self.upload_folder = Path(tempfile.gettempdir()) / "gateway_plugins_upload"
        self.upload_folder.mkdir(parents=True, exist_ok=True)
        self.app.config['UPLOAD_FOLDER'] = str(self.upload_folder)
        self.app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB

        self._init_auth_config()
        
        self._register_routes()
        
        log.info("Plugin API initialized on %s:%s", host, port)

    def _init_auth_config(self):
        auth_type_value = self.auth_config.get('type')
        if self.auth_config and auth_type_value is None:
            raise ValueError("Plugin API auth config is present but 'type' is missing")

        self.auth_type = (auth_type_value or 'disabled').lower()
        self.auth_header = self.auth_config.get('header', 'Authorization')
        self.token_prefix = self.auth_config.get('token_prefix', 'Bearer ')

        self.static_tokens = {
            token.strip() for token in self.auth_config.get('tokens', []) if token and token.strip()
        }

        self.tb_validation_url = self.auth_config.get('validation_url')
        self.tb_auth_header = self.auth_config.get('tb_auth_header', 'X-Authorization')
        self.tb_cache_ttl = int(self.auth_config.get('cache_ttl_sec', 60))
        self.tb_allowed_authorities = set(self.auth_config.get('allowed_authorities', ['TENANT_ADMIN', 'SYS_ADMIN']))

        if self.auth_type not in {'disabled', 'static_token', 'thingsboard_jwt'}:
            raise ValueError(f"Unknown plugin API auth type: {self.auth_type}")

        if self.auth_type == 'static_token' and not self.static_tokens:
            log.warning("Plugin API static token auth is enabled but no tokens are configured")

        if self.auth_type == 'thingsboard_jwt' and not self.tb_validation_url:
            raise ValueError("Plugin API auth type 'thingsboard_jwt' requires 'validation_url'")

        if self.auth_type == 'disabled':
            log.warning("Plugin API auth is disabled. Do not expose %s:%s to untrusted networks", self.host, self.port)
        else:
            log.info("Plugin API auth enabled: %s", self.auth_type)

    def _extract_token(self) -> Optional[str]:
        auth_value = request.headers.get(self.auth_header, '').strip()

        if not auth_value:
            return None

        if self.token_prefix and auth_value.startswith(self.token_prefix):
            return auth_value[len(self.token_prefix):].strip()

        if self.token_prefix:
            return None

        return auth_value

    def _validate_tb_jwt(self, token: str) -> Tuple[bool, Optional[str]]:
        cache_record = self._auth_cache.get(token)
        now = time.monotonic()
        if cache_record and cache_record[0] > now:
            user_info = cache_record[1]
            authority = user_info.get('authority')
            if authority in self.tb_allowed_authorities:
                return True, None
            return False, f"Insufficient authority: {authority}"

        try:
            response = requests.get(
                self.tb_validation_url,
                headers={self.tb_auth_header: f"Bearer {token}"},
                timeout=5
            )
        except requests.RequestException as e:
            log.warning("Failed to validate token against ThingsBoard: %s", e)
            return False, "Token validation service unavailable"

        if response.status_code != 200:
            return False, "Invalid or expired token"

        try:
            user_info = response.json()
        except json.JSONDecodeError:
            return False, "Invalid validation response"

        authority = user_info.get('authority')
        if authority not in self.tb_allowed_authorities:
            return False, f"Insufficient authority: {authority}"

        self._auth_cache[token] = (now + self.tb_cache_ttl, user_info)
        return True, None

    def _authorize_request(self):
        if self.auth_type == 'disabled':
            return None

        token = self._extract_token()
        if not token:
            return jsonify({'success': False, 'error': 'Missing or invalid auth token'}), 401

        if self.auth_type == 'static_token':
            for configured_token in self.static_tokens:
                if hmac.compare_digest(configured_token, token):
                    return None
            return jsonify({'success': False, 'error': 'Invalid auth token'}), 401

        if self.auth_type == 'thingsboard_jwt':
            valid, error = self._validate_tb_jwt(token)
            if not valid:
                return jsonify({'success': False, 'error': error}), 403

        return None
    
    def _register_routes(self):
        """注册API路由"""

        @self.app.before_request
        def authorize_request():
            if request.path == '/api/plugins/health' or request.method == 'OPTIONS':
                return None
            return self._authorize_request()
        
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
