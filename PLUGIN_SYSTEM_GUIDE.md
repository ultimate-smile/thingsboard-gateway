# ThingsBoard Gateway 插件系统使用指南

## 目录
1. [概述](#概述)
2. [系统架构](#系统架构)
3. [快速开始](#快速开始)
4. [创建插件](#创建插件)
5. [安装插件](#安装插件)
6. [REST API](#rest-api)
7. [示例](#示例)

---

## 概述

插件系统允许您动态地添加、删除和管理ThingsBoard Gateway的连接器，无需重新编译或重启整个网关服务。

### 主要特性

- **动态加载**: 通过上传文件即可立即使用新的连接器
- **版本管理**: 支持插件版本控制和依赖管理
- **REST API**: 提供完整的HTTP接口管理插件
- **命令行工具**: 提供便捷的CLI工具
- **隔离性**: 插件独立安装，互不影响
- **安全性**: 插件验证和依赖检查

---

## 系统架构

### 核心组件

```
plugin_system/
├── plugin_manager.py          # 插件管理器（安装、卸载、启用、禁用）
├── plugin_spec.py            # 插件规范和元数据定义
├── plugin_api.py             # REST API服务器
└── gateway_plugin_integration.py  # 网关集成
```

### 插件结构

一个标准的插件包结构：

```
my_connector_plugin.zip
├── plugin.json               # 插件清单文件（必需）
├── my_connector.py          # 连接器实现
├── my_uplink_converter.py   # 上行转换器
├── my_downlink_converter.py # 下行转换器
└── README.md                # 说明文档（可选）
```

---

## 快速开始

### 1. 启用插件系统

在网关配置文件 `tb_gateway.yaml` 或 `tb_gateway.json` 中添加插件配置：

```json
{
  "plugins": {
    "enabled": true,
    "enable_api": true,
    "api_host": "0.0.0.0",
    "api_port": 9001
  }
}
```

### 2. 安装现有插件

#### 方法1: 使用命令行工具

```bash
# 列出所有插件
python tools/plugin_installer.py list

# 安装插件
python tools/plugin_installer.py install /path/to/plugin.zip

# 卸载插件
python tools/plugin_installer.py uninstall plugin_name

# 查看插件信息
python tools/plugin_installer.py info plugin_name
```

#### 方法2: 使用REST API

```bash
# 上传并安装插件
curl -X POST http://localhost:9001/api/plugins/upload \
  -F "file=@plugin.zip" \
  -F "force=false"

# 列出所有插件
curl http://localhost:9001/api/plugins

# 卸载插件
curl -X DELETE http://localhost:9001/api/plugins/plugin_name
```

#### 方法3: 使用Web界面

访问 `http://localhost:9001/api/plugins` 查看所有API端点。

### 3. 使用插件连接器

安装插件后，在连接器配置中使用：

```json
{
  "connectors": [
    {
      "name": "My OPC UA Connector",
      "type": "opcua",
      "configuration": "opcua.json"
    }
  ]
}
```

---

## 创建插件

### 步骤1: 准备连接器代码

确保您的连接器继承自 `Connector` 基类：

```python
from thingsboard_gateway.connectors.connector import Connector

class MyConnector(Connector):
    def __init__(self, gateway, config, connector_type):
        super().__init__()
        # 初始化代码
    
    def open(self):
        # 打开连接
        pass
    
    def close(self):
        # 关闭连接
        pass
    
    # 实现其他必需方法...
```

### 步骤2: 创建插件清单

创建 `plugin.json` 文件：

```json
{
  "name": "my_connector_plugin",
  "version": "1.0.0",
  "plugin_type": "connector",
  "connector_type": "myprotocol",
  "display_name": "My Protocol Connector",
  "description": "A connector for My Protocol",
  "author": "Your Name",
  "license": "Apache-2.0",
  "python_requires": ">=3.7",
  "dependencies": [
    "some-package>=1.0.0"
  ],
  "entry_point": "MyConnector",
  "module_name": "my_connector",
  "gateway_version": ">=3.0"
}
```

### 步骤3: 打包插件

#### 方法1: 使用打包工具

```bash
python tools/plugin_packager.py \
  /path/to/connector/source \
  -o my_connector_plugin.zip \
  -t myprotocol \
  -v 1.0.0 \
  -d "My Protocol Connector" \
  -a "Your Name" \
  --deps "package1>=1.0,package2>=2.0"
```

#### 方法2: 手动打包

```bash
cd /path/to/connector/source
zip -r my_connector_plugin.zip .
```

---

## 安装插件

### 使用命令行工具

```bash
# 基本安装
python tools/plugin_installer.py install my_connector_plugin.zip

# 强制安装（覆盖已有版本）
python tools/plugin_installer.py install my_connector_plugin.zip --force

# 指定配置目录
python tools/plugin_installer.py -c /path/to/config install plugin.zip
```

### 使用Python API

```python
from thingsboard_gateway.gateway.plugin_system import PluginManager

# 创建插件管理器
manager = PluginManager(
    plugins_dir="/path/to/plugins",
    config_dir="/path/to/config"
)

# 安装插件
success, message = manager.install_plugin("plugin.zip", force=False)
if success:
    print(f"安装成功: {message}")
else:
    print(f"安装失败: {message}")

# 列出插件
plugins = manager.list_plugins()
for plugin in plugins:
    print(f"{plugin['name']} v{plugin['version']}")
```

---

## REST API

### 端点列表

#### 1. 健康检查
```http
GET /api/plugins/health
```

响应：
```json
{
  "success": true,
  "status": "healthy",
  "plugin_count": 5
}
```

#### 2. 列出所有插件
```http
GET /api/plugins?enabled=true
```

响应：
```json
{
  "success": true,
  "plugins": [
    {
      "name": "opcua_connector_plugin",
      "version": "1.0.0",
      "type": "connector",
      "connector_type": "opcua",
      "display_name": "OPC UA Connector",
      "description": "OPC UA protocol connector",
      "enabled": true,
      "install_path": "/path/to/plugins/opcua",
      "install_time": 1704412800.0
    }
  ],
  "count": 1
}
```

#### 3. 获取插件详情
```http
GET /api/plugins/{plugin_name}
```

#### 4. 上传并安装插件
```http
POST /api/plugins/upload
Content-Type: multipart/form-data

file: plugin.zip
force: false
```

响应：
```json
{
  "success": true,
  "message": "Plugin opcua_connector_plugin installed successfully"
}
```

#### 5. 卸载插件
```http
DELETE /api/plugins/{plugin_name}
```

#### 6. 启用插件
```http
POST /api/plugins/{plugin_name}/enable
```

#### 7. 禁用插件
```http
POST /api/plugins/{plugin_name}/disable
```

---

## 示例

### 示例1: 将现有OPC UA连接器打包为插件

```bash
# 1. 打包连接器
python tools/plugin_packager.py \
  thingsboard_gateway/connectors/opcua \
  -o opcua_connector_plugin.zip \
  -t opcua \
  -v 1.0.0 \
  -d "OPC UA Connector Plugin" \
  -a "ThingsBoard" \
  --deps "asyncua==1.1.5"

# 2. 安装插件
python tools/plugin_installer.py install opcua_connector_plugin.zip

# 3. 验证安装
python tools/plugin_installer.py list
```

### 示例2: 通过REST API管理插件

```bash
# 上传插件
curl -X POST http://localhost:9001/api/plugins/upload \
  -F "file=@opcua_connector_plugin.zip"

# 列出所有插件
curl http://localhost:9001/api/plugins | jq .

# 禁用插件
curl -X POST http://localhost:9001/api/plugins/opcua_connector_plugin/disable

# 启用插件
curl -X POST http://localhost:9001/api/plugins/opcua_connector_plugin/enable

# 卸载插件
curl -X DELETE http://localhost:9001/api/plugins/opcua_connector_plugin
```

### 示例3: 创建自定义连接器插件

```python
# my_custom_connector.py
from thingsboard_gateway.connectors.connector import Connector
import logging

log = logging.getLogger(__name__)

class MyCustomConnector(Connector):
    def __init__(self, gateway, config, connector_type):
        super().__init__()
        self._gateway = gateway
        self._config = config
        self._connector_type = connector_type
        self._connected = False
        log.info("MyCustomConnector initialized")
    
    def open(self):
        log.info("Opening MyCustomConnector")
        self._connected = True
    
    def close(self):
        log.info("Closing MyCustomConnector")
        self._connected = False
    
    def get_id(self):
        return self._config.get('id')
    
    def get_name(self):
        return self._config.get('name')
    
    def get_type(self):
        return self._connector_type
    
    def get_config(self):
        return self._config
    
    def is_connected(self):
        return self._connected
    
    def is_stopped(self):
        return not self._connected
    
    def on_attributes_update(self, content):
        log.info("Received attribute update: %s", content)
    
    def server_side_rpc_handler(self, content):
        log.info("Received RPC request: %s", content)
```

创建 `plugin.json`:

```json
{
  "name": "my_custom_connector_plugin",
  "version": "1.0.0",
  "plugin_type": "connector",
  "connector_type": "mycustom",
  "display_name": "My Custom Connector",
  "description": "A custom connector implementation",
  "author": "Your Name",
  "license": "Apache-2.0",
  "python_requires": ">=3.7",
  "dependencies": [],
  "entry_point": "MyCustomConnector",
  "module_name": "my_custom_connector",
  "gateway_version": ">=3.0"
}
```

打包并安装：

```bash
# 打包
python tools/plugin_packager.py \
  /path/to/my_custom_connector \
  -o my_custom_connector_plugin.zip \
  -t mycustom \
  -v 1.0.0

# 安装
python tools/plugin_installer.py install my_custom_connector_plugin.zip
```

在网关配置中使用：

```json
{
  "connectors": [
    {
      "name": "My Custom Connector",
      "type": "mycustom",
      "configuration": "mycustom.json"
    }
  ]
}
```

---

## 最佳实践

### 1. 版本管理
- 使用语义化版本号（如1.0.0）
- 在更新时递增版本号
- 记录版本变更

### 2. 依赖管理
- 明确指定所有Python依赖
- 使用版本约束（如`package>=1.0.0,<2.0.0`）
- 避免依赖冲突

### 3. 错误处理
- 实现完善的错误处理
- 提供有意义的日志信息
- 优雅地处理失败情况

### 4. 文档
- 为插件提供README.md
- 说明配置选项
- 提供使用示例

### 5. 测试
- 在安装前测试插件
- 验证与网关的兼容性
- 测试升级和回滚

---

## 故障排除

### 问题1: 插件安装失败

**原因**: 可能是依赖缺失或版本不兼容

**解决**:
```bash
# 查看详细错误信息
python tools/plugin_installer.py install plugin.zip

# 手动安装依赖
pip install required-package
```

### 问题2: 连接器无法加载

**原因**: 插件路径未正确添加或模块名不正确

**解决**:
1. 检查插件是否已启用
2. 验证`plugin.json`中的`module_name`和`entry_point`
3. 检查日志中的错误信息

### 问题3: REST API无法访问

**原因**: Flask未安装或API未启用

**解决**:
```bash
# 安装Flask
pip install flask

# 检查配置
# 确保配置文件中 "plugins.enable_api": true
```

---

## 高级用法

### 自定义插件路径

```python
from thingsboard_gateway.tb_utility.tb_loader import TBModuleLoader

# 添加自定义插件路径
TBModuleLoader.add_plugin_path("/custom/path/to/plugins")
```

### 程序化管理插件

```python
from thingsboard_gateway.gateway.plugin_system import PluginManager

manager = PluginManager(
    plugins_dir="/path/to/plugins",
    config_dir="/path/to/config"
)

# 批量安装插件
plugins_to_install = ["plugin1.zip", "plugin2.zip", "plugin3.zip"]
for plugin_file in plugins_to_install:
    success, msg = manager.install_plugin(plugin_file)
    print(f"{plugin_file}: {msg}")

# 启用所有插件
for plugin_name in manager.registry.keys():
    manager.enable_plugin(plugin_name)
```

---

## 参考资料

- [ThingsBoard Gateway文档](https://thingsboard.io/docs/iot-gateway/)
- [连接器开发指南](https://thingsboard.io/docs/iot-gateway/custom-connector/)
- [API参考](./API_REFERENCE.md)

---

## 贡献

欢迎贡献插件和改进建议！请访问项目仓库提交Issue或Pull Request。

## 许可证

Apache License 2.0
