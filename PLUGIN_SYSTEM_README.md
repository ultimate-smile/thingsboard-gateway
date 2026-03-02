# ThingsBoard Gateway 插件系统

## 概述

本项目为ThingsBoard Gateway实现了完整的插件化系统，允许通过上传文件的方式动态添加和管理连接器，无需重新编译或重启网关。

## 核心特性

✅ **动态加载** - 通过ZIP文件上传即可立即使用新连接器  
✅ **REST API** - 完整的HTTP接口管理插件  
✅ **命令行工具** - 便捷的CLI工具  
✅ **版本管理** - 支持插件版本控制和依赖管理  
✅ **安全隔离** - 插件独立安装，互不影响  
✅ **自动发现** - 自动加载启用的插件路径  

## 快速开始

### 1. 启用插件系统

在网关配置文件中添加：

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

### 2. 打包示例插件

```bash
# 使用打包工具
python thingsboard_gateway/tools/plugin_packager.py \
  examples/example_plugin \
  -o example_connector_plugin.zip \
  -t example \
  -v 1.0.0
```

### 3. 安装插件

```bash
# 方法1: 命令行
python thingsboard_gateway/tools/plugin_installer.py install example_connector_plugin.zip

# 方法2: REST API
curl -X POST http://localhost:9001/api/plugins/upload \
  -F "file=@example_connector_plugin.zip"
```

### 4. 验证安装

```bash
# 列出所有插件
python thingsboard_gateway/tools/plugin_installer.py list

# 或通过API
curl http://localhost:9001/api/plugins
```

## 项目结构

```
thingsboard_gateway/
├── gateway/
│   └── plugin_system/              # 插件系统核心
│       ├── __init__.py
│       ├── plugin_manager.py       # 插件管理器
│       ├── plugin_spec.py          # 插件规范
│       ├── plugin_api.py           # REST API服务
│       └── gateway_plugin_integration.py  # 网关集成
│
├── tb_utility/
│   └── tb_loader.py                # 扩展支持动态插件路径
│
thingsboard_gateway/tools/
├── plugin_packager.py              # 打包工具
└── plugin_installer.py             # 安装工具

examples/
└── example_plugin/                 # 示例插件
    ├── plugin.json
    ├── example_connector.py
    └── README.md
```

## 使用场景

### 场景1: 添加新协议支持

假设您需要添加OPC DA支持：

```bash
# 1. 将OPC DA连接器打包
python thingsboard_gateway/tools/plugin_packager.py \
  thingsboard_gateway/connectors/opcda \
  -o opcda_plugin.zip \
  -t opcda \
  -v 1.0.0 \
  --deps "pywin32>=300"

# 2. 安装插件
python thingsboard_gateway/tools/plugin_installer.py install opcda_plugin.zip

# 3. 配置连接器
# 在config/tb_gateway.json中添加：
{
  "connectors": [
    {
      "name": "OPC DA Connector",
      "type": "opcda",
      "configuration": "opcda.json"
    }
  ]
}

# 4. 重启网关，OPC DA连接器即可使用
```

### 场景2: 通过Web界面管理

```bash
# 启动网关后，REST API自动运行在9001端口

# 上传插件
curl -X POST http://localhost:9001/api/plugins/upload \
  -F "file=@myconnector.zip"

# 列出所有插件
curl http://localhost:9001/api/plugins

# 启用/禁用插件
curl -X POST http://localhost:9001/api/plugins/myconnector/enable
curl -X POST http://localhost:9001/api/plugins/myconnector/disable

# 卸载插件
curl -X DELETE http://localhost:9001/api/plugins/myconnector
```

### 场景3: 开发自定义连接器

```python
# 1. 创建连接器类
# my_connector.py
from thingsboard_gateway.connectors.connector import Connector

class MyConnector(Connector):
    def __init__(self, gateway, config, connector_type):
        super().__init__()
        # 初始化代码
    
    def open(self):
        # 打开连接
        pass
    
    # 实现其他方法...

# 2. 创建plugin.json
{
  "name": "my_connector_plugin",
  "version": "1.0.0",
  "connector_type": "myprotocol",
  "entry_point": "MyConnector",
  "module_name": "my_connector"
}

# 3. 打包
python thingsboard_gateway/tools/plugin_packager.py . -o my_plugin.zip -t myprotocol -v 1.0.0

# 4. 安装
python thingsboard_gateway/tools/plugin_installer.py install my_plugin.zip
```

## REST API端点

| 方法 | 端点 | 描述 |
|------|------|------|
| GET | `/api/plugins` | 列出所有插件 |
| GET | `/api/plugins/{name}` | 获取插件详情 |
| POST | `/api/plugins/upload` | 上传并安装插件 |
| DELETE | `/api/plugins/{name}` | 卸载插件 |
| POST | `/api/plugins/{name}/enable` | 启用插件 |
| POST | `/api/plugins/{name}/disable` | 禁用插件 |
| GET | `/api/plugins/health` | 健康检查 |

## 命令行工具

### plugin_packager.py

```bash
python thingsboard_gateway/tools/plugin_packager.py SOURCE_DIR \
  -o OUTPUT_FILE \
  -t CONNECTOR_TYPE \
  -v VERSION \
  [-d DESCRIPTION] \
  [-a AUTHOR] \
  [--deps DEPENDENCIES]
```

### plugin_installer.py

```bash
# 列出插件
python thingsboard_gateway/tools/plugin_installer.py list [--enabled]

# 安装插件
python thingsboard_gateway/tools/plugin_installer.py install PLUGIN_FILE [--force]

# 卸载插件
python thingsboard_gateway/tools/plugin_installer.py uninstall PLUGIN_NAME

# 启用/禁用插件
python thingsboard_gateway/tools/plugin_installer.py enable PLUGIN_NAME
python thingsboard_gateway/tools/plugin_installer.py disable PLUGIN_NAME

# 查看插件信息
python thingsboard_gateway/tools/plugin_installer.py info PLUGIN_NAME
```

## 插件结构规范

标准的插件包结构：

```
my_plugin.zip
├── plugin.json                  # 必需：插件清单
├── my_connector.py             # 必需：连接器实现
├── my_uplink_converter.py      # 可选：上行转换器
├── my_downlink_converter.py    # 可选：下行转换器
└── README.md                   # 推荐：说明文档
```

`plugin.json` 必需字段：

```json
{
  "name": "unique_plugin_name",
  "version": "1.0.0",
  "plugin_type": "connector",
  "connector_type": "myprotocol",
  "entry_point": "MyConnectorClass",
  "module_name": "my_connector_file"
}
```

## 工作原理

1. **插件安装**
   - 解压ZIP包到`config/plugins/{connector_type}/`
   - 验证`plugin.json`
   - 安装Python依赖
   - 注册到插件注册表

2. **插件加载**
   - 网关启动时读取插件注册表
   - 将启用的插件路径添加到`TBModuleLoader`
   - 连接器加载时优先从插件路径搜索

3. **动态管理**
   - 通过REST API或CLI工具管理
   - 启用/禁用立即生效
   - 安装/卸载需要重启网关

## 实现细节

### 核心组件

1. **PluginManager** (`plugin_manager.py`)
   - 插件生命周期管理
   - 依赖安装
   - 版本验证

2. **PluginSpec** (`plugin_spec.py`)
   - 插件元数据定义
   - 规范验证

3. **PluginAPI** (`plugin_api.py`)
   - Flask REST服务器
   - 文件上传处理

4. **GatewayPluginIntegration** (`gateway_plugin_integration.py`)
   - 与网关服务集成
   - 自动加载插件路径

5. **TBModuleLoader扩展** (`tb_loader.py`)
   - 动态插件路径支持
   - 优先级搜索

## 示例插件

项目包含一个完整的示例插件（`examples/example_plugin/`），演示：

- 完整的连接器实现
- 定期数据采集
- RPC请求处理
- 属性更新处理
- 多设备管理

可以直接使用或作为开发模板。

## 依赖

核心依赖：
- Python >= 3.7
- packaging（版本检查）

REST API依赖（可选）：
- Flask（安装：`pip install flask`）

## 最佳实践

1. **版本管理** - 使用语义化版本号
2. **依赖声明** - 明确指定所有依赖及版本
3. **错误处理** - 实现完善的异常处理
4. **日志记录** - 提供详细的日志信息
5. **文档** - 为插件提供README和配置说明
6. **测试** - 在安装前充分测试

## 故障排除

### 问题：插件无法加载

**检查**:
1. 插件是否已启用：`python thingsboard_gateway/tools/plugin_installer.py list`
2. 查看网关日志是否有错误信息
3. 验证`plugin.json`中的`entry_point`和`module_name`

### 问题：REST API无法访问

**解决**:
```bash
# 安装Flask
pip install flask

# 检查配置文件中plugins.enable_api是否为true
# 检查防火墙是否开放9001端口
```

### 问题：依赖安装失败

**解决**:
```bash
# 手动安装依赖
pip install required-package

# 或在plugin.json中修改依赖版本
```

## 更多信息

详细文档请参阅：
- [完整使用指南](PLUGIN_SYSTEM_GUIDE.md)
- [示例插件](examples/example_plugin/README.md)
- [API参考](https://thingsboard.io/docs/iot-gateway/)

## 许可证

Apache License 2.0

---

**实现完成！** 现在您可以通过简单的文件上传来添加新的连接器支持！🎉
