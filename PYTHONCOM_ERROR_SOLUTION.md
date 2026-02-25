# pythoncom 错误解决方案

## 问题描述

当运行 OPC DA 测试代码时出现以下错误:

```python
NameError: name 'pythoncom' is not defined
```

完整错误堆栈:
```
File "/path/to/OpenOPC.py", line 155, in __init__
    pythoncom.CoInitialize()
    ^^^^^^^^^
NameError: name 'pythoncom' is not defined
```

## 原因分析

`pythoncom` 是 `pywin32` 包的一部分，提供 Python 到 Windows COM/DCOM 的绑定。该错误表明:

1. **pywin32 未安装** - Windows 平台缺少必需的依赖
2. **非 Windows 平台** - 在 macOS/Linux 上运行，OPC DA 是 Windows 专有技术
3. **导入失败** - pywin32 安装不完整或未正确配置

## 快速解决方案

### 👉 如果你在 Windows 上:

```bash
# 1. 安装 pywin32
pip install pywin32

# 2. 运行安装后配置
python -m pywin32_postinstall -install

# 3. 安装 OpenOPC
pip install OpenOPC-Python3x

# 4. 验证安装
python -c "import pythoncom; import OpenOPC; print('✓ 安装成功')"
```

### 👉 如果你在 macOS/Linux 上:

你有三个选择:

#### 选项 1: Mock 模式 (推荐用于开发)

```json
{
  "server": {
    "name": "Matrikon.OPC.Simulation.1",
    "host": "localhost",
    "useMockOpc": true,
    "pollPeriodInMillis": 5000
  }
}
```

#### 选项 2: OpenOPC Gateway Server (推荐用于生产)

在 Windows 机器上运行:
```bash
python -m OpenOPC.OpenOPCService
```

在 macOS/Linux 上连接:
```python
import OpenOPC
opc = OpenOPC.open_client('192.168.1.100')  # Windows IP
opc.connect('Matrikon.OPC.Simulation.1')
```

#### 选项 3: 使用虚拟机

安装 Windows 虚拟机，在其中运行完整的 OPC DA 环境。

## 测试你的用例

你的测试代码:

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

### Windows 上运行:

1. 按照上面的 Windows 解决方案安装依赖
2. 确保 OPC 服务器正在运行 (如 Matrikon OPC Simulation Server)
3. 直接运行代码

### macOS 上运行 (使用 Mock):

```python
# 使用 Mock 模式
from thingsboard_gateway.connectors.opcda import mock_openopc as OpenOPC

# 创建客户端
opc = OpenOPC.client()

# 连接到服务器 (模拟)
opc.connect('Matrikon.OPC.Simulation.1')

# 列出所有标签 (模拟数据)
tags = opc.list()
print(tags)
print(f"找到 {len(tags)} 个模拟标签")

# 读取一个标签 (模拟数据)
value = opc.read('Random.Int4')
print(f"Random.Int4 值: {value}")

# 关闭连接
opc.close()
```

## 诊断工具

运行诊断脚本以检查系统配置:

```bash
cd thingsboard_gateway/connectors/opcda
python diagnose_pythoncom.py
```

该工具将:
- ✓ 检查操作系统平台
- ✓ 验证 Python 版本
- ✓ 测试 pythoncom 和 OpenOPC 安装
- ✓ 提供具体的修复建议
- ✓ 测试 Mock 模式可用性

## 完整文档

更详细的信息请参考:

- **[TROUBLESHOOTING_PYTHONCOM.md](thingsboard_gateway/connectors/opcda/TROUBLESHOOTING_PYTHONCOM.md)** 
  完整的故障排除指南，包含所有错误场景和解决方案

- **[PLATFORM_GUIDE.md](thingsboard_gateway/connectors/opcda/PLATFORM_GUIDE.md)** 
  跨平台使用指南，详细说明各平台的最佳实践

- **[INSTALLATION.md](thingsboard_gateway/connectors/opcda/INSTALLATION.md)** 
  完整的安装步骤，包括 DCOM 配置

- **[README.md](thingsboard_gateway/connectors/opcda/README.md)** 
  连接器使用手册和配置说明

## 推荐方案总结

| 场景 | 推荐方案 | 难度 |
|------|---------|------|
| Windows 开发/生产 | 直接安装 pywin32 + OpenOPC | ⭐ 简单 |
| macOS/Linux 开发 | Mock 模式 | ⭐ 简单 |
| macOS/Linux 生产 | OpenOPC Gateway Server | ⭐⭐ 中等 |
| 长期方案 | 迁移到 OPC UA | ⭐⭐⭐ 复杂但值得 |

## 需要帮助？

如果以上方案都无法解决你的问题，请:

1. 运行诊断工具: `python diagnose_pythoncom.py`
2. 查看详细文档 (见上面链接)
3. 提供以下信息寻求帮助:
   - 操作系统 (Windows/macOS/Linux)
   - Python 版本
   - 错误完整堆栈
   - 已尝试的解决方案

## 快速命令参考

```bash
# Windows - 完整安装
pip install pywin32 OpenOPC-Python3x
python -m pywin32_postinstall -install

# 验证安装
python -c "import pythoncom; print('✓ pythoncom OK')"
python -c "import OpenOPC; print('✓ OpenOPC OK')"

# 测试 Mock 模式
python -c "from thingsboard_gateway.connectors.opcda import mock_openopc; print('✓ Mock OK')"

# 运行诊断
cd thingsboard_gateway/connectors/opcda
python diagnose_pythoncom.py
```

---

**最后更新**: 2025-12-29  
**适用版本**: ThingsBoard Gateway with OPC DA Connector
