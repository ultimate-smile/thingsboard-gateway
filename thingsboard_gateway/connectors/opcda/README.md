# OPC DA Connector

## 概述

OPC DA (OLE for Process Control Data Access) 连接器允许 IoT Gateway 从 OPC DA 服务器采集数据。OPC DA 是一种广泛使用的工业自动化协议标准。

## 功能特性

- **数据采集**: 从 OPC DA 服务器读取标签数据
- **属性更新**: 支持更新设备属性到 OPC DA 标签
- **RPC 支持**: 支持读取和写入 OPC DA 标签的 RPC 命令
- **多设备支持**: 可以配置多个虚拟设备，每个设备有自己的标签映射
- **时间戳支持**: 支持使用网关时间戳或 OPC 服务器时间戳
- **质量检查**: 自动检查 OPC DA 数据质量

## 依赖要求

```bash
pip install OpenOPC-Python3x
```

**注意**: OPC DA 通常需要 Windows 操作系统，因为它基于 DCOM 技术。对于 Linux 系统，可能需要使用 OPC DA 网关或代理。

## 配置说明

### 基本配置结构

```json
{
  "name": "OPC DA Connector",
  "type": "opcda",
  "logLevel": "INFO",
  "configuration": "opcda.json",
  "configurationJson": {
    "server": {
      "name": "Matrikon.OPC.Simulation.1",
      "host": "localhost",
      "timeoutInMillis": 5000,
      "pollPeriodInMillis": 5000
    },
    "mapping": [
      {
        "deviceInfo": {
          "deviceNameExpression": "设备名称",
          "deviceProfileExpression": "设备类型"
        },
        "timeseries": [...],
        "attributes": [...],
        "attributes_updates": [...],
        "rpc_methods": [...]
      }
    ]
  }
}
```

### 服务器配置 (server)

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| name | string | 是 | - | OPC DA 服务器的 ProgID（例如：Matrikon.OPC.Simulation.1） |
| host | string | 否 | localhost | OPC DA 服务器主机地址 |
| timeoutInMillis | integer | 否 | 5000 | 连接超时时间（毫秒） |
| pollPeriodInMillis | integer | 否 | 5000 | 数据采集周期（毫秒） |

### 设备映射 (mapping)

#### deviceInfo

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| deviceNameExpression | string | 是 | 设备名称 |
| deviceProfileExpression | string | 否 | 设备类型/配置文件名称 |

#### timeseries（遥测数据）

| 参数 | 类型 | 必需 | 默认值 | 描述 |
|------|------|------|--------|------|
| key | string | 是 | - | ThingsBoard 中的键名 |
| tag | string | 是 | - | OPC DA 标签路径 |
| timestampLocation | string | 否 | gateway | 时间戳来源：gateway（网关时间）或 source（OPC 服务器时间） |

#### attributes（属性）

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| key | string | 是 | ThingsBoard 中的属性键名 |
| tag | string | 是 | OPC DA 标签路径 |

#### attributes_updates（属性更新）

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| key | string | 是 | ThingsBoard 中的属性键名 |
| tag | string | 是 | 要写入的 OPC DA 标签路径 |

#### rpc_methods（RPC 方法）

支持的 RPC 方法：

1. **read** - 读取标签值
```json
{
  "method": "read",
  "params": "Random.Int4"
}
```

2. **write** - 写入标签值
```json
{
  "method": "write",
  "params": {
    "tag": "Bucket Brigade.Real8",
    "value": 123.45
  }
}
```

## 完整配置示例

```json
{
  "name": "OPC DA Connector",
  "type": "opcda",
  "logLevel": "INFO",
  "configurationJson": {
    "server": {
      "name": "Matrikon.OPC.Simulation.1",
      "host": "localhost",
      "timeoutInMillis": 5000,
      "pollPeriodInMillis": 5000
    },
    "mapping": [
      {
        "deviceInfo": {
          "deviceNameExpression": "Temperature Sensor",
          "deviceProfileExpression": "default"
        },
        "timeseries": [
          {
            "key": "temperature",
            "tag": "Random.Real8",
            "timestampLocation": "source"
          },
          {
            "key": "humidity",
            "tag": "Random.Int4",
            "timestampLocation": "gateway"
          }
        ],
        "attributes": [
          {
            "key": "model",
            "tag": "Random.String"
          }
        ],
        "attributes_updates": [
          {
            "key": "temperatureSetpoint",
            "tag": "Bucket Brigade.Real8"
          }
        ],
        "rpc_methods": []
      }
    ]
  }
}
```

## 常见 OPC DA 服务器 ProgID

- **Matrikon OPC Simulation Server**: `Matrikon.OPC.Simulation.1`
- **Kepware**: `Kepware.KEPServerEX.V6`
- **RSLinx OPC Server**: `RSLinx OPC Server`
- **Siemens S7**: `OPC.SimaticNET`

## 故障排除

### 连接问题

1. **无法连接到 OPC 服务器**
   - 确保 OPC DA 服务器正在运行
   - 检查服务器 ProgID 是否正确
   - 验证 DCOM 配置（Windows）
   - 检查防火墙设置

2. **标签读取失败**
   - 验证标签路径是否正确
   - 检查标签是否存在于 OPC 服务器中
   - 确认用户权限

3. **质量代码不是 192**
   - 192 表示数据质量良好
   - 其他值表示数据质量问题，检查 OPC 服务器状态

### 性能优化

- 调整 `pollPeriodInMillis` 以平衡数据新鲜度和系统负载
- 减少不必要的标签读取
- 使用 OPC DA 组订阅（如果支持）

## 限制

- OPC DA 主要在 Windows 平台上运行
- 不支持 OPC DA 事件和报警（需要 OPC AE）
- 不支持历史数据访问（需要 OPC HDA）

## 迁移到 OPC UA

如果可能，建议迁移到 OPC UA 连接器，因为：
- OPC UA 是跨平台的
- 提供更好的安全性
- 是现代工业物联网的标准

## 许可证

Apache License 2.0
