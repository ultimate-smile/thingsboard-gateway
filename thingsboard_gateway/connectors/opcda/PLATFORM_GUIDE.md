# OPC DA 跨平台使用指南

## 平台兼容性概述

OPC DA (OLE for Process Control Data Access) 是基于 Windows DCOM 技术的工业通信协议。不同平台的支持情况如下：

| 平台 | 原生支持 | 推荐方案 | 难度 |
|------|---------|---------|------|
| **Windows** | ✅ 完全支持 | 直接使用 | ⭐ 简单 |
| **macOS** | ❌ 不支持 | 网关模式 / Mock | ⭐⭐⭐ 中等 |
| **Linux** | ❌ 不支持 | 网关模式 / Mock | ⭐⭐⭐ 中等 |

## 方案对比

### 方案 1: Windows 平台 (生产环境推荐)

**优点:**
- ✅ 完全支持所有 OPC DA 功能
- ✅ 性能最佳
- ✅ 配置简单
- ✅ 稳定可靠

**缺点:**
- ❌ 需要 Windows 操作系统
- ❌ 需要配置 DCOM

**适用场景:**
- 生产环境部署
- 连接真实的 OPC DA 服务器
- 需要完整的 OPC DA 功能

**设置步骤:**

1. **安装 Python 依赖**
```bash
pip install pywin32
python -m pywin32_postinstall -install
pip install OpenOPC-Python3x
```

2. **验证安装**
```python
import pythoncom
print("✓ pythoncom 可用")

import OpenOPC
opc = OpenOPC.client()
print("✓ OpenOPC 可用")
```

3. **配置连接器** (`opcda.json`)
```json
{
  "name": "OPC DA Connector",
  "type": "opcda",
  "configuration": "opcda.json",
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "localhost",
    "pollPeriodInMillis": 5000
  },
  "mapping": [...]
}
```

---

### 方案 2: OpenOPC Gateway Server (跨平台生产环境)

**优点:**
- ✅ 支持 macOS/Linux 访问 Windows OPC 服务器
- ✅ 真实的 OPC DA 连接
- ✅ 适合生产环境

**缺点:**
- ❌ 需要额外的 Windows 机器作为网关
- ❌ 增加了网络延迟
- ❌ 配置较复杂

**适用场景:**
- macOS/Linux 上的生产环境
- 远程访问 OPC DA 服务器
- 多个客户端共享 OPC 服务器

**架构图:**
```
┌─────────────────┐
│  macOS/Linux    │
│  开发机/服务器   │
│                 │
│  ThingsBoard    │
│  Gateway        │
│  + OpenOPC客户端 │
└────────┬────────┘
         │ TCP/IP
         │ (Port 7766)
         ▼
┌─────────────────┐
│  Windows 机器    │
│                 │
│  OpenOPC        │
│  Gateway Server │
└────────┬────────┘
         │ DCOM
         ▼
┌─────────────────┐
│  OPC DA Server  │
│  (本地或远程)    │
└─────────────────┘
```

**设置步骤:**

**步骤 1: 在 Windows 机器上设置网关服务器**

1. 安装依赖:
```bash
pip install pywin32
python -m pywin32_postinstall -install
pip install OpenOPC-Python3x
```

2. 启动 OpenOPC Gateway Server:
```bash
# 方法 A: 命令行模式
python -m OpenOPC.OpenOPCService

# 方法 B: 作为 Windows 服务安装
python OpenOPC_install_service.py
```

3. 配置防火墙:
```powershell
# 允许端口 7766
New-NetFirewallRule -DisplayName "OpenOPC Gateway" -Direction Inbound -Protocol TCP -LocalPort 7766 -Action Allow
```

**步骤 2: 在 macOS/Linux 上配置客户端**

1. 安装 OpenOPC (不需要 pywin32):
```bash
pip install OpenOPC-Python3x
```

2. 测试连接:
```python
import OpenOPC

# 连接到网关服务器
opc = OpenOPC.open_client('192.168.1.100')  # Windows 网关 IP

# 连接到 OPC 服务器
opc.connect('Matrikon.OPC.Simulation.1')

# 读取数据
value = opc.read('Random.Int4')
print(value)

opc.close()
```

3. 配置连接器 (`opcda.json`):
```json
{
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "192.168.1.100",
    "gatewayMode": true,
    "gatewayPort": 7766,
    "pollPeriodInMillis": 5000
  },
  "mapping": [...]
}
```

---

### 方案 3: Mock OPC 模式 (开发/测试环境)

**优点:**
- ✅ 支持所有平台 (Windows/macOS/Linux)
- ✅ 无需真实 OPC 服务器
- ✅ 配置简单
- ✅ 快速开发和测试

**缺点:**
- ❌ 仅用于开发/测试
- ❌ 模拟数据,非真实数据
- ❌ 不适合生产环境

**适用场景:**
- 本地开发和调试
- 单元测试和集成测试
- CI/CD 流水线
- 演示和培训

**设置步骤:**

1. **无需额外安装** (已包含在连接器中)

2. **配置连接器** (`opcda_mock.json`)
```json
{
  "name": "OPC DA Connector (Mock)",
  "type": "opcda",
  "configuration": "opcda.json",
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "localhost",
    "useMockOpc": true,
    "pollPeriodInMillis": 5000
  },
  "mapping": [
    {
      "deviceInfo": {
        "deviceNameExpression": "Simulated Device",
        "deviceProfileExpression": "default"
      },
      "timeseries": [
        {
          "key": "temperature",
          "tag": "Random.Real8"
        },
        {
          "key": "pressure",
          "tag": "Random.Int4"
        },
        {
          "key": "flow",
          "tag": "Bucket.Brigade.Real4"
        }
      ],
      "attributes": [
        {
          "key": "status",
          "tag": "Bucket.Brigade.String"
        }
      ]
    }
  ]
}
```

3. **直接使用 Mock 客户端**
```python
from thingsboard_gateway.connectors.opcda import mock_openopc

# 创建 Mock 客户端
opc = mock_openopc.client()

# 连接(模拟)
opc.connect('Matrikon.OPC.Simulation.1')

# 读取模拟数据
tags = opc.list('Random.*')
print(f"Available tags: {tags}")

value = opc.read('Random.Int4')
print(f"Random.Int4: {value}")

# 关闭
opc.close()
```

4. **添加自定义模拟标签**
```python
from thingsboard_gateway.connectors.opcda import mock_openopc
import random

opc = mock_openopc.client()
opc.connect('Matrikon.OPC.Simulation.1')

# 添加自定义标签
opc.add_mock_tag('Custom.Temperature', lambda: 20 + random.uniform(-5, 5))
opc.add_mock_tag('Custom.Humidity', lambda: 50 + random.uniform(-10, 10))

# 读取自定义标签
temp = opc.read('Custom.Temperature')
humidity = opc.read('Custom.Humidity')
print(f"Temperature: {temp}")
print(f"Humidity: {humidity}")

opc.close()
```

---

### 方案 4: 虚拟机 / Docker (开发环境)

**优点:**
- ✅ 在 macOS/Linux 上运行 Windows
- ✅ 完整的 Windows 环境
- ✅ 可以运行真实的 OPC 服务器

**缺点:**
- ❌ 需要 Windows 许可证
- ❌ 资源消耗较大
- ❌ 配置复杂

**适用场景:**
- 在 macOS/Linux 上开发但需要真实 OPC 连接
- 测试环境
- 临时验证

**选项 A: VirtualBox / VMware**

1. 安装虚拟机软件
2. 创建 Windows VM
3. 在 VM 中安装:
   - Python
   - pywin32
   - OpenOPC-Python3x
   - OPC DA Server
4. 配置网络桥接或端口转发

**选项 B: Docker Desktop with Windows Containers**

仅限 Windows 10/11 Pro:
```dockerfile
FROM mcr.microsoft.com/windows/servercore:ltsc2019

# 安装 Python 和依赖
RUN powershell -Command \
    Invoke-WebRequest ... && \
    pip install pywin32 OpenOPC-Python3x

# 复制应用
COPY . /app
WORKDIR /app

CMD ["python", "-m", "thingsboard_gateway"]
```

---

### 方案 5: 迁移到 OPC UA (长期推荐)

**优点:**
- ✅ 真正跨平台
- ✅ 更现代、更安全
- ✅ 更好的性能
- ✅ 无需 DCOM

**缺点:**
- ❌ 需要 OPC UA 服务器
- ❌ 可能需要硬件/软件升级

**适用场景:**
- 新项目
- 长期维护的系统
- 需要跨平台支持

**迁移步骤:**

1. 检查设备是否支持 OPC UA
2. 安装 OPC UA 服务器 (或升级固件)
3. 使用 ThingsBoard OPC UA 连接器:

```json
{
  "name": "OPC UA Connector",
  "type": "opcua",
  "configuration": "opcua.json",
  "server": {
    "url": "opc.tcp://localhost:4840",
    "security": "Basic256Sha256"
  },
  "mapping": [...]
}
```

---

## 决策流程图

```
开始
  │
  ├─ 是否有真实的 OPC DA 服务器需要连接?
  │    │
  │    ├─ 是 ──┐
  │    │       │
  │    └─ 否 ──┼─→ 仅开发/测试? ──→ 使用 Mock 模式 (方案 3)
  │            │
  │            └─ 运行平台是 Windows?
  │                 │
  │                 ├─ 是 ──→ 直接使用 (方案 1) ✅ 推荐
  │                 │
  │                 └─ 否 (macOS/Linux)
  │                      │
  │                      ├─ 可以部署 Windows 网关?
  │                      │    │
  │                      │    ├─ 是 ──→ OpenOPC Gateway (方案 2)
  │                      │    │
  │                      │    └─ 否 ──→ 使用虚拟机 (方案 4)
  │                      │
  │                      └─ 长期方案? ──→ 迁移到 OPC UA (方案 5) ⭐ 最佳
```

---

## 常见问题解答 (FAQ)

### Q1: 我在 macOS 上遇到 "pythoncom is not defined" 错误,怎么办?

**A:** 这是正常的,因为 OPC DA 需要 Windows。解决方案:
- **开发**: 启用 Mock 模式 (`"useMockOpc": true`)
- **生产**: 使用 OpenOPC Gateway Server (方案 2)
- **长期**: 考虑迁移到 OPC UA (方案 5)

### Q2: 我必须使用 Windows 吗?

**A:** 对于生产环境的 OPC DA,是的。但有以下替代方案:
- OpenOPC Gateway Server (Windows 作为网关)
- Mock 模式 (开发/测试)
- OPC UA (跨平台的现代协议)

### Q3: Mock 模式的数据是真实的吗?

**A:** 不是。Mock 模式生成模拟数据,仅用于:
- 开发和调试连接器逻辑
- 单元测试
- UI 演示
- 不应在生产环境使用

### Q4: OpenOPC Gateway Server 稳定吗?

**A:** 是的,Gateway 模式广泛用于生产环境,用于:
- 跨平台访问
- 集中管理 OPC 连接
- 负载均衡

### Q5: 如何在 Linux Docker 容器中运行 OPC DA?

**A:** 不能直接运行。但可以:
1. 容器中运行 ThingsBoard Gateway
2. 通过网络连接到 Windows Gateway Server
3. Gateway Server 连接到 OPC DA Server

```yaml
# docker-compose.yml
services:
  gateway:
    image: thingsboard/tb-gateway
    environment:
      - OPC_GATEWAY_HOST=192.168.1.100  # Windows 网关
    volumes:
      - ./config:/etc/tb-gateway/config
```

### Q6: 我应该选择哪个方案?

| 场景 | 推荐方案 |
|------|---------|
| Windows 生产环境 | 方案 1 (直接) |
| Linux/macOS 生产环境 | 方案 2 (Gateway) |
| 本地开发 (任何平台) | 方案 3 (Mock) |
| 测试环境 | 方案 3 (Mock) 或方案 4 (VM) |
| 新项目 | 方案 5 (OPC UA) |

---

## 快速开始指令

### Windows 用户
```bash
# 安装依赖
pip install pywin32 OpenOPC-Python3x
python -m pywin32_postinstall -install

# 验证
python -c "import pythoncom; import OpenOPC; print('✓ Ready')"

# 使用标准配置
# 在 opcda.json 中设置: "useMockOpc": false
```

### macOS/Linux 用户 (开发)
```bash
# 无需安装 pywin32
pip install OpenOPC-Python3x  # (可选,如果要用真实网关)

# 使用 Mock 配置
# 在 opcda.json 中设置: "useMockOpc": true

# 测试
python -c "from thingsboard_gateway.connectors.opcda import mock_openopc; print('✓ Ready')"
```

### macOS/Linux 用户 (生产)
```bash
# 设置 Windows Gateway Server (在 Windows 机器上)
python -m OpenOPC.OpenOPCService

# 配置连接器连接到网关
# 在 opcda.json 中设置:
# "host": "192.168.1.100"  # Windows 网关 IP
# "useMockOpc": false
```

---

## 获取帮助

- **连接器问题**: 查看 `TROUBLESHOOTING_PYTHONCOM.md`
- **配置问题**: 查看 `README.md`
- **安装问题**: 查看 `INSTALLATION.md`
- **快速入门**: 查看 `QUICKSTART.md`

---

## 总结

- **Windows**: 直接使用,最佳体验 ✅
- **macOS/Linux 开发**: Mock 模式 ✅
- **macOS/Linux 生产**: OpenOPC Gateway ✅
- **未来**: OPC UA 跨平台 ⭐

选择适合你的方案,开始使用 ThingsBoard Gateway OPC DA 连接器!
