#!/usr/bin/env python3
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
OPC DA pythoncom 诊断工具

此脚本检查你的系统是否正确配置以运行 OPC DA 连接器。
它会测试所有必需的依赖项并提供详细的错误信息和解决方案。

使用方法:
    python diagnose_pythoncom.py
"""

import sys
import platform
import os
from typing import Tuple, List


def print_header(title: str):
    """打印带格式的标题"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


def print_section(title: str):
    """打印节标题"""
    print(f"\n[{title}]")
    print("-" * 70)


def check_result(success: bool, message: str, details: str = ""):
    """打印检查结果"""
    status = "✓" if success else "✗"
    color = "\033[92m" if success else "\033[91m"  # Green or Red
    reset = "\033[0m"
    
    print(f"{color}{status}{reset} {message}")
    if details:
        print(f"  {details}")


def check_python_version() -> Tuple[bool, str]:
    """检查 Python 版本"""
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major == 3 and version.minor >= 7:
        return True, f"Python {version_str}"
    else:
        return False, f"Python {version_str} (需要 3.7+)"


def check_platform() -> Tuple[bool, str, str]:
    """检查操作系统平台"""
    system = platform.system()
    release = platform.release()
    machine = platform.machine()
    
    is_windows = system == "Windows"
    platform_str = f"{system} {release} ({machine})"
    
    if is_windows:
        recommendation = "Windows 平台 - 支持原生 OPC DA"
    else:
        recommendation = f"{system} 平台 - 需要使用 Gateway 模式或 Mock 模式"
    
    return is_windows, platform_str, recommendation


def check_pythoncom() -> Tuple[bool, str, List[str]]:
    """检查 pythoncom 模块"""
    try:
        import pythoncom
        version = getattr(pythoncom, 'version', 'unknown')
        return True, f"pythoncom 已安装 (版本: {version})", []
    except ImportError as e:
        suggestions = [
            "安装 pywin32: pip install pywin32",
            "运行安装后脚本: python -m pywin32_postinstall -install",
            "在 Windows 上以管理员权限运行"
        ]
        return False, f"pythoncom 未安装: {e}", suggestions


def check_win32com() -> Tuple[bool, str, List[str]]:
    """检查 win32com 模块"""
    try:
        import win32com
        return True, "win32com 已安装", []
    except ImportError as e:
        suggestions = [
            "安装 pywin32: pip install pywin32",
            "运行安装后脚本: python -m pywin32_postinstall -install"
        ]
        return False, f"win32com 未安装: {e}", suggestions


def check_openopc() -> Tuple[bool, str, List[str]]:
    """检查 OpenOPC 库"""
    try:
        import OpenOPC
        version = getattr(OpenOPC, '__version__', 'unknown')
        return True, f"OpenOPC 已安装 (版本: {version})", []
    except ImportError as e:
        suggestions = [
            "安装 OpenOPC: pip install OpenOPC-Python3x"
        ]
        return False, f"OpenOPC 未安装: {e}", suggestions


def check_mock_openopc() -> Tuple[bool, str]:
    """检查 Mock OpenOPC 模块"""
    try:
        from thingsboard_gateway.connectors.opcda import mock_openopc
        return True, "Mock OpenOPC 可用"
    except ImportError as e:
        return False, f"Mock OpenOPC 不可用: {e}"


def test_openopc_client() -> Tuple[bool, str, List[str]]:
    """测试创建 OpenOPC 客户端"""
    try:
        import OpenOPC
        client = OpenOPC.client()
        return True, "OpenOPC 客户端创建成功", []
    except NameError as e:
        if 'pythoncom' in str(e):
            suggestions = [
                "pythoncom 未定义 - 这是最常见的错误",
                "解决方案:",
                "  1. 如果在 Windows: 安装并配置 pywin32",
                "  2. 如果在 macOS/Linux: 使用 OpenOPC Gateway 或 Mock 模式",
                "  3. 详细信息请查看 TROUBLESHOOTING_PYTHONCOM.md"
            ]
            return False, f"pythoncom 错误: {e}", suggestions
        else:
            return False, f"NameError: {e}", [str(e)]
    except Exception as e:
        return False, f"错误: {e}", [str(e)]


def test_mock_client() -> Tuple[bool, str]:
    """测试创建 Mock OPC 客户端"""
    try:
        from thingsboard_gateway.connectors.opcda import mock_openopc
        client = mock_openopc.client()
        client.connect('Matrikon.OPC.Simulation.1')
        tags = client.list('Random.*')
        value = client.read('Random.Int4')
        client.close()
        return True, f"Mock 客户端工作正常 (读取了 {len(tags)} 个标签)"
    except Exception as e:
        return False, f"Mock 客户端错误: {e}"


def get_recommendations(is_windows: bool, has_pythoncom: bool, has_openopc: bool):
    """根据检查结果提供建议"""
    recommendations = []
    
    if is_windows:
        if not has_pythoncom:
            recommendations.append(
                "🔧 Windows 平台但缺少 pythoncom:\n"
                "   1. 安装 pywin32: pip install pywin32\n"
                "   2. 运行配置: python -m pywin32_postinstall -install\n"
                "   3. 重启终端\n"
                "   4. 以管理员权限运行如果仍有问题"
            )
        if not has_openopc:
            recommendations.append(
                "🔧 安装 OpenOPC:\n"
                "   pip install OpenOPC-Python3x"
            )
        if has_pythoncom and has_openopc:
            recommendations.append(
                "✅ 系统已就绪!\n"
                "   你可以直接使用 OPC DA 连接器连接到真实的 OPC 服务器\n"
                "   配置示例: tests/unit/connectors/opcda/data/opcda_simple_config.json"
            )
    else:
        recommendations.append(
            f"⚠️  非 Windows 平台 - OPC DA 需要 Windows 或特殊配置\n"
            "   \n"
            "   选项 1: Mock 模式 (推荐用于开发)\n"
            "   - 配置: \"useMockOpc\": true\n"
            "   - 示例: tests/unit/connectors/opcda/data/opcda_mock_config.json\n"
            "   \n"
            "   选项 2: OpenOPC Gateway Server\n"
            "   - 在 Windows 机器上运行: python -m OpenOPC.OpenOPCService\n"
            "   - 配置连接器指向网关 IP\n"
            "   \n"
            "   选项 3: 虚拟机\n"
            "   - 使用 VirtualBox/VMware 运行 Windows\n"
            "   - 在虚拟机中运行完整的 ThingsBoard Gateway\n"
            "   \n"
            "   选项 4: 迁移到 OPC UA (长期推荐)\n"
            "   - 使用 ThingsBoard Gateway 的 OPC UA 连接器\n"
            "   - 完全跨平台支持"
        )
    
    return recommendations


def main():
    """主诊断函数"""
    print_header("OPC DA pythoncom 诊断工具")
    print("此工具将检查你的系统配置以确定 OPC DA 连接器的可用性")
    
    # 系统信息
    print_section("1. 系统信息")
    
    py_ok, py_version = check_python_version()
    check_result(py_ok, f"Python 版本: {py_version}")
    
    is_windows, platform_str, platform_rec = check_platform()
    check_result(True, f"操作系统: {platform_str}")
    print(f"  → {platform_rec}")
    
    # 依赖检查
    print_section("2. 依赖项检查")
    
    pythoncom_ok, pythoncom_msg, pythoncom_suggestions = check_pythoncom()
    check_result(pythoncom_ok, pythoncom_msg)
    for suggestion in pythoncom_suggestions:
        print(f"    → {suggestion}")
    
    win32com_ok, win32com_msg, win32com_suggestions = check_win32com()
    check_result(win32com_ok, win32com_msg)
    for suggestion in win32com_suggestions:
        print(f"    → {suggestion}")
    
    openopc_ok, openopc_msg, openopc_suggestions = check_openopc()
    check_result(openopc_ok, openopc_msg)
    for suggestion in openopc_suggestions:
        print(f"    → {suggestion}")
    
    mock_ok, mock_msg = check_mock_openopc()
    check_result(mock_ok, mock_msg)
    
    # 功能测试
    print_section("3. 功能测试")
    
    if openopc_ok:
        client_ok, client_msg, client_suggestions = test_openopc_client()
        check_result(client_ok, f"OpenOPC 客户端: {client_msg}")
        for suggestion in client_suggestions:
            print(f"    → {suggestion}")
    else:
        check_result(False, "OpenOPC 客户端: 跳过 (OpenOPC 未安装)")
    
    if mock_ok:
        mock_client_ok, mock_client_msg = test_mock_client()
        check_result(mock_client_ok, f"Mock 客户端: {mock_client_msg}")
    else:
        check_result(False, "Mock 客户端: 不可用")
    
    # 推荐方案
    print_section("4. 推荐方案")
    
    recommendations = get_recommendations(is_windows, pythoncom_ok, openopc_ok)
    for i, rec in enumerate(recommendations, 1):
        print(f"\n{rec}")
    
    # 总结
    print_section("5. 总结")
    
    if is_windows and pythoncom_ok and openopc_ok:
        print("\n✅ 恭喜! 你的系统已准备好运行 OPC DA 连接器!")
        print("   下一步:")
        print("   1. 配置连接器 (参考 README.md)")
        print("   2. 启动 OPC DA 服务器")
        print("   3. 运行 ThingsBoard Gateway")
    elif mock_ok:
        print("\n⚠️  系统不支持原生 OPC DA,但 Mock 模式可用")
        print("   建议:")
        print("   - 开发/测试: 使用 Mock 模式")
        print("   - 生产: 使用 OpenOPC Gateway Server 或迁移到 OPC UA")
    else:
        print("\n❌ 系统尚未准备好运行 OPC DA 连接器")
        print("   请按照上述推荐方案进行配置")
    
    # 文档链接
    print_section("6. 更多帮助")
    print("""
相关文档:
  - TROUBLESHOOTING_PYTHONCOM.md - pythoncom 错误详细解决方案
  - PLATFORM_GUIDE.md           - 跨平台使用指南
  - INSTALLATION.md              - 完整安装指南
  - README.md                    - 连接器使用手册
  - QUICKSTART.md                - 5 分钟快速入门

在线资源:
  - ThingsBoard Gateway: https://thingsboard.io/docs/iot-gateway/
  - OpenOPC GitHub: https://github.com/iterativ/openopc
  - pywin32 文档: https://pypi.org/project/pywin32/
    """)
    
    print("\n" + "=" * 70)
    print("诊断完成!")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n诊断已取消")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n诊断过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
