# OPC DA 连接器快速入门

本指南将帮助你在 5 分钟内启动并运行 OPC DA 连接器。

## 前提条件

- ✅ Python 3.7+
- ✅ ThingsBoard IoT Gateway 已安装
- ✅ Windows 操作系统（推荐）
- ✅ OPC DA 服务器（例如：Matrikon OPC Simulation Server）

## 步骤 1: 安装依赖

```bash
pip install OpenOPC-Python3x
```

## 步骤 2: 安装测试 OPC 服务器

如果你还没有 OPC DA 服务器，可以使用免费的模拟服务器：

1. 下载 [Matrikon OPC Simulation Server](https://www.matrikonopc.com/)
2. 安装并启动服务器
3. 验证服务器在系统托盘中运行

## 步骤 3: 创建配置文件

在网关配置目录中创建 `opcda.json`:

```json
{
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "localhost",
    "pollPeriodInMillis": 5000
  },
  "mapping": [
    {
      "deviceInfo": {
        "deviceNameExpression": "My First Device",
        "deviceProfileExpression": "default"
      },
      "timeseries": [
        {
          "key": "temperature",
          "tag": "Random.Real8"
        },
        {
          "key": "counter",
          "tag": "Random.Int4"
        }
      ],
      "attributes": [
        {
          "key": "status",
          "tag": "Random.String"
        }
      ]
    }
  ]
}
```

## 步骤 4: 配置网关

在 ThingsBoard Gateway 的 `tb_gateway.yaml` 中添加：

```yaml
connectors:
  - name: OPC DA Connector
    type: opcda
    configuration: opcda.json
    logLevel: INFO
```

## 步骤 5: 启动网关

```bash
# Linux/Mac
python3 -m thingsboard_gateway

# Windows
python -m thingsboard_gateway
```

## 步骤 6: 验证数据

1. 登录到 ThingsBoard 平台
2. 导航到"设备"页面
3. 你应该看到名为 "My First Device" 的设备
4. 点击设备查看遥测数据

## 配置说明

### 服务器配置

| 参数 | 说明 | 示例 |
|------|------|------|
| name | OPC 服务器的 ProgID | `Matrikon.OPC.Simulation.1` |
| host | 服务器地址 | `localhost` 或 `192.168.1.100` |
| pollPeriodInMillis | 采集周期（毫秒） | `5000`（5秒） |

### 标签配置

#### 遥测数据（Timeseries）
定期上报的测量值，如传感器读数：

```json
{
  "key": "temperature",        // ThingsBoard 中的键名
  "tag": "Random.Real8"        // OPC DA 标签路径
}
```

#### 属性（Attributes）
设备的静态或半静态信息：

```json
{
  "key": "model",
  "tag": "Device.Model"
}
```

## 常见标签示例

如果使用 Matrikon OPC Simulation Server，以下是一些可用的标签：

| 标签路径 | 数据类型 | 说明 |
|---------|---------|------|
| `Random.Int4` | 整数 | 随机整数值 |
| `Random.Real8` | 浮点数 | 随机浮点数 |
| `Random.String` | 字符串 | 随机字符串 |
| `Random.Boolean` | 布尔值 | 随机布尔值 |
| `Bucket Brigade.Int4` | 整数 | 可写入的整数 |
| `Bucket Brigade.Real8` | 浮点数 | 可写入的浮点数 |

## 测试连接

### 使用 Python 脚本测试

创建 `test_connection.py`:

```python
import OpenOPC

try:
    # 创建客户端
    opc = OpenOPC.client()
    
    # 连接到服务器
    print("连接到 OPC 服务器...")
    opc.connect('Matrikon.OPC.Simulation.1')
    print("✓ 连接成功！")
    
    # 列出一些标签
    print("\n可用标签:")
    tags = opc.list('Random.*')
    for tag in tags[:5]:  # 显示前5个
        print(f"  - {tag}")
    
    # 读取标签值
    print("\n读取标签值:")
    value = opc.read('Random.Int4')
    print(f"  Random.Int4 = {value}")
    
    value = opc.read('Random.Real8')
    print(f"  Random.Real8 = {value}")
    
    # 关闭连接
    opc.close()
    print("\n✓ 测试完成！")
    
except Exception as e:
    print(f"✗ 错误: {e}")
```

运行：
```bash
python test_connection.py
```

## 高级功能

### 1. 属性更新

允许从 ThingsBoard 写入值到 OPC DA：

```json
{
  "attributes_updates": [
    {
      "key": "setpoint",
      "tag": "Bucket Brigade.Real8"
    }
  ]
}
```

在 ThingsBoard 中更新 `setpoint` 属性，值将写入到 `Bucket Brigade.Real8` 标签。

### 2. RPC 命令

#### 读取标签
```json
{
  "method": "read",
  "params": "Random.Int4"
}
```

#### 写入标签
```json
{
  "method": "write",
  "params": {
    "tag": "Bucket Brigade.Real8",
    "value": 123.45
  }
}
```

### 3. 时间戳选项

```json
{
  "key": "temperature",
  "tag": "Random.Real8",
  "timestampLocation": "source"  // 使用 OPC 服务器时间戳
}
```

可选值：
- `gateway`（默认）：使用网关时间戳
- `source`：使用 OPC 服务器提供的时间戳

## 故障排除

### 问题：无法连接到 OPC 服务器

**检查清单：**
1. ✓ OPC 服务器是否正在运行？
2. ✓ ProgID 是否正确？
3. ✓ DCOM 配置是否正确？（运行 `dcomcnfg`）
4. ✓ 防火墙是否阻止连接？

### 问题：标签读取失败

**检查：**
1. 标签路径是否正确？
2. 使用 OPC 测试客户端验证标签存在
3. 检查 OPC 服务器日志

### 问题：性能慢

**优化：**
1. 增加 `pollPeriodInMillis` 值
2. 减少标签数量
3. 使用本地连接而非远程

## 下一步

- 📖 阅读 [完整文档](README.md)
- 🔧 查看 [安装指南](INSTALLATION.md)
- 💡 探索 [配置示例](../../tests/unit/connectors/opcda/data/)
- 🌐 访问 [ThingsBoard 文档](https://thingsboard.io/docs/)

## 获取帮助

- GitHub Issues: 报告问题
- 官方论坛: 提问和讨论
- 文档: 详细参考资料

---

**祝你使用愉快！** 🎉

如果这个快速入门指南对你有帮助，请考虑为项目加星 ⭐
