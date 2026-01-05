# Example Connector Plugin

这是一个示例连接器插件，用于演示如何创建和使用ThingsBoard Gateway插件系统。

## 功能

- 定期发送模拟遥测数据
- 支持RPC请求处理
- 支持属性更新
- 多设备管理

## 配置

创建配置文件 `config/example.json`:

```json
{
  "id": "example_connector_001",
  "name": "Example Connector",
  "pollInterval": 5,
  "devices": [
    {
      "deviceName": "Example Device 1",
      "deviceType": "sensor"
    },
    {
      "deviceName": "Example Device 2",
      "deviceType": "sensor"
    }
  ]
}
```

在主配置文件中添加连接器：

```json
{
  "connectors": [
    {
      "name": "Example Connector",
      "type": "example",
      "configuration": "example.json"
    }
  ]
}
```

## 安装

```bash
# 打包插件
cd examples/example_plugin
zip -r example_connector_plugin.zip .

# 安装插件
python ../../tools/plugin_installer.py install example_connector_plugin.zip
```

## 使用

安装后，连接器会自动启动并开始发送数据。

### 查看日志

```
2025-01-05 10:00:00 - INFO - ExampleConnector 'Example Connector' opened successfully
2025-01-05 10:00:00 - INFO - Device 'Example Device 1' registered
2025-01-05 10:00:00 - INFO - Device 'Example Device 2' registered
2025-01-05 10:00:05 - DEBUG - Sent telemetry for device 'Example Device 1': {'temperature': 25.67, 'humidity': 62.34, 'pressure': 1013.25, 'status': 'active'}
```

### RPC示例

发送RPC请求获取值：

```json
{
  "method": "getValue",
  "params": {}
}
```

响应：

```json
{
  "value": 42,
  "timestamp": 1704412800000
}
```

发送RPC请求设置值：

```json
{
  "method": "setValue",
  "params": {
    "value": 100
  }
}
```

响应：

```json
{
  "success": true,
  "value": 100
}
```

## 开发

基于这个示例，您可以开发自己的连接器：

1. 复制 `example_connector.py` 并重命名
2. 修改 `plugin.json` 中的元数据
3. 实现您的数据采集逻辑
4. 打包并安装

## 许可证

Apache License 2.0
