# OPC DA 连接器安装指南

## 系统要求

### Windows 系统
OPC DA 主要在 Windows 上运行，因为它基于 Microsoft DCOM 技术。

**要求：**
- Windows 7/8/10/11 或 Windows Server 2012+
- Python 3.7+
- OPC DA 服务器（例如：Matrikon OPC Simulation Server）

### Linux 系统
Linux 上运行 OPC DA 需要额外的组件：
- OPC DA Gateway（例如：Matrikon OPC Tunneller）
- 或使用 Wine（不推荐用于生产环境）

## 安装步骤

### 1. 安装 Python 依赖

#### 方法 A: 使用 pip
```bash
pip install OpenOPC-Python3x
```

#### 方法 B: 使用 requirements.txt
创建 `requirements.txt` 文件：
```
OpenOPC-Python3x>=1.3.1
```

然后安装：
```bash
pip install -r requirements.txt
```

### 2. 配置 Windows DCOM

OPC DA 使用 DCOM 进行通信，需要正确配置：

#### 2.1 配置 DCOM 安全设置

1. 运行 `dcomcnfg`（组件服务）
2. 展开"组件服务" → "计算机" → "我的电脑"
3. 右键"我的电脑"，选择"属性"
4. 在"COM 安全"选项卡中：
   - 点击"访问权限"中的"编辑限制"
   - 添加 ANONYMOUS LOGON 和 Everyone，授予"本地访问"和"远程访问"权限
   - 对"启动和激活权限"做同样的操作

#### 2.2 配置 OPC Server DCOM 设置

1. 在"组件服务"中，展开"DCOM 配置"
2. 找到你的 OPC 服务器（例如：Matrikon.OPC.Simulation）
3. 右键 → "属性"
4. 在"常规"选项卡中，设置"身份验证级别"为"无"
5. 在"安全"选项卡中，配置启动、访问和配置权限
6. 在"标识"选项卡中，选择"交互式用户"

### 3. 安装 OPC DA 服务器（用于测试）

#### Matrikon OPC Simulation Server
这是一个免费的 OPC DA 模拟服务器，适合开发和测试。

1. 访问 [Matrikon 官网](https://www.matrikonopc.com/)
2. 下载并安装 Matrikon OPC Simulation Server
3. 安装后，服务器会自动启动
4. 服务器 ProgID: `Matrikon.OPC.Simulation.1`

#### 其他 OPC 服务器
- **Kepware**: 商业 OPC 服务器，功能强大
- **Industrial Gateway Server**: 开源选项

### 4. 验证安装

#### 4.1 测试 OpenOPC 库
```python
import OpenOPC

# 创建客户端
opc = OpenOPC.client()

# 连接到服务器
opc.connect('Matrikon.OPC.Simulation.1')

# 列出所有标签
tags = opc.list()
print(tags)

# 读取一个标签
value = opc.read('Random.Int4')
print(value)

# 关闭连接
opc.close()
```

#### 4.2 测试连接器
创建测试配置文件 `test_opcda.json`:
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
        "deviceNameExpression": "Test Device"
      },
      "timeseries": [
        {
          "key": "temperature",
          "tag": "Random.Real8"
        }
      ],
      "attributes": []
    }
  ]
}
```

## 常见问题

### 问题 1: ImportError: No module named 'OpenOPC'
**解决方案:**
```bash
pip install --upgrade pip
pip install OpenOPC-Python3x
```

### 问题 2: 无法连接到 OPC 服务器
**可能原因:**
1. OPC 服务器未运行
2. DCOM 配置不正确
3. 防火墙阻止连接
4. ProgID 不正确

**解决步骤:**
1. 确认 OPC 服务器正在运行
2. 使用 OPC 测试客户端（如 Matrikon OPC Explorer）验证服务器
3. 检查 Windows 防火墙设置
4. 验证 ProgID（使用 `opcenumerate` 命令）

### 问题 3: Access Denied 错误
**解决方案:**
- 以管理员权限运行 Python 脚本
- 配置 DCOM 权限（参见第 2 步）

### 问题 4: 在 Linux 上运行
**解决方案:**
1. 安装 OPC DA Tunneller 在 Windows 机器上
2. 配置连接器连接到隧道服务器
3. 或者考虑使用 OPC UA 连接器代替

## 远程连接

要连接到远程 OPC DA 服务器：

### 1. 在远程机器上配置 DCOM
按照上述 DCOM 配置步骤操作。

### 2. 配置连接器
```json
{
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "192.168.1.100",
    "pollPeriodInMillis": 5000
  }
}
```

### 3. 配置防火墙
确保以下端口开放：
- TCP 135 (RPC Endpoint Mapper)
- TCP 随机端口范围（通常 1024-65535）

## 性能优化

### 1. 调整轮询周期
```json
{
  "server": {
    "pollPeriodInMillis": 1000  // 更快的采集
  }
}
```

### 2. 减少标签数量
只采集必要的标签，减少网络和处理开销。

### 3. 使用本地连接
尽可能在本地运行连接器和 OPC 服务器。

## 安全建议

1. **使用专用账户**: 为 OPC 通信创建专用 Windows 账户
2. **限制权限**: 只授予必要的 DCOM 权限
3. **防火墙规则**: 只允许必要的 IP 地址访问
4. **定期更新**: 保持 OPC 服务器和客户端库更新

## 生产环境部署

### 1. 系统配置
- 使用专用的 Windows 服务器或虚拟机
- 配置系统自动启动
- 设置日志轮转

### 2. 监控
- 监控连接器状态
- 设置告警通知
- 定期检查日志

### 3. 备份
- 备份配置文件
- 记录 DCOM 设置
- 维护 OPC 服务器配置备份

## 获取帮助

如果遇到问题：
1. 查看日志文件
2. 使用 OPC 测试工具验证服务器连接
3. 检查 ThingsBoard Gateway 文档
4. 联系技术支持

## 相关资源

- [OpenOPC GitHub](https://github.com/iterativ/openopc)
- [OPC Foundation](https://opcfoundation.org/)
- [ThingsBoard Gateway 文档](https://thingsboard.io/docs/iot-gateway/)
- [Matrikon OPC 资源](https://www.matrikonopc.com/)
