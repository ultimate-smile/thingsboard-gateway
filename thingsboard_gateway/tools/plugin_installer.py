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
插件安装工具
用于从命令行安装、卸载和管理插件
"""

import argparse
import json
import os
import sys
from pathlib import Path

TOOLS_DIR = Path(__file__).resolve().parent
GATEWAY_DIR = TOOLS_DIR.parent
REPO_DIR = GATEWAY_DIR.parent

# 添加项目根目录到路径
sys.path.insert(0, str(REPO_DIR))

from thingsboard_gateway.gateway.plugin_system.plugin_manager import PluginManager


def get_default_config_dir():
    """获取默认配置目录"""
    # 尝试从环境变量获取
    config_dir = os.environ.get('TB_GATEWAY_CONFIG_DIR')
    if config_dir:
        return config_dir
    
    # 使用默认路径
    return str(GATEWAY_DIR / 'config')


def list_plugins(plugin_manager, enabled_only=False):
    """列出插件"""
    plugins = plugin_manager.list_plugins(enabled_only=enabled_only)
    
    if not plugins:
        print("没有找到插件")
        return
    
    print(f"\n找到 {len(plugins)} 个插件:\n")
    print(f"{'名称':<30} {'版本':<10} {'类型':<15} {'状态':<10}")
    print("-" * 70)
    
    for plugin in plugins:
        status = "已启用" if plugin['enabled'] else "已禁用"
        print(f"{plugin['name']:<30} {plugin['version']:<10} "
              f"{plugin['connector_type']:<15} {status:<10}")


def install_plugin(plugin_manager, plugin_file, force=False):
    """安装插件"""
    print(f"正在安装插件: {plugin_file}")
    
    success, message = plugin_manager.install_plugin(plugin_file, force=force)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ 安装失败: {message}")
        sys.exit(1)


def uninstall_plugin(plugin_manager, plugin_name):
    """卸载插件"""
    print(f"正在卸载插件: {plugin_name}")
    
    success, message = plugin_manager.uninstall_plugin(plugin_name)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ 卸载失败: {message}")
        sys.exit(1)


def enable_plugin(plugin_manager, plugin_name):
    """启用插件"""
    success, message = plugin_manager.enable_plugin(plugin_name)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        sys.exit(1)


def disable_plugin(plugin_manager, plugin_name):
    """禁用插件"""
    success, message = plugin_manager.disable_plugin(plugin_name)
    
    if success:
        print(f"✓ {message}")
    else:
        print(f"✗ {message}")
        sys.exit(1)


def show_plugin_info(plugin_manager, plugin_name):
    """显示插件详细信息"""
    plugin = plugin_manager.get_plugin(plugin_name)
    
    if not plugin:
        print(f"插件未找到: {plugin_name}")
        sys.exit(1)
    
    metadata = plugin.metadata
    
    print(f"\n插件信息:")
    print(f"  名称: {metadata.name}")
    print(f"  显示名称: {metadata.display_name}")
    print(f"  版本: {metadata.version}")
    print(f"  类型: {metadata.plugin_type.value}")
    print(f"  连接器类型: {metadata.connector_type}")
    print(f"  描述: {metadata.description}")
    print(f"  作者: {metadata.author}")
    print(f"  许可证: {metadata.license}")
    print(f"  Python要求: {metadata.python_requires}")
    print(f"  网关版本要求: {metadata.gateway_version}")
    print(f"  依赖: {', '.join(metadata.dependencies) if metadata.dependencies else '无'}")
    print(f"  入口点: {metadata.entry_point}")
    print(f"  模块名: {metadata.module_name}")
    print(f"  安装路径: {plugin.install_path}")
    print(f"  状态: {'已启用' if plugin.enabled else '已禁用'}")
    
    if plugin.install_time:
        from datetime import datetime
        install_date = datetime.fromtimestamp(plugin.install_time)
        print(f"  安装时间: {install_date.strftime('%Y-%m-%d %H:%M:%S')}")


def main():
    parser = argparse.ArgumentParser(
        description='ThingsBoard Gateway 插件管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 列出所有插件
  %(prog)s list
  
  # 安装插件
  %(prog)s install opcua_plugin.zip
  
  # 强制安装（覆盖已有插件）
  %(prog)s install opcua_plugin.zip --force
  
  # 卸载插件
  %(prog)s uninstall opcua_connector_plugin
  
  # 启用/禁用插件
  %(prog)s enable opcua_connector_plugin
  %(prog)s disable opcua_connector_plugin
  
  # 查看插件信息
  %(prog)s info opcua_connector_plugin
        """
    )
    
    parser.add_argument('-c', '--config-dir', 
                       help='配置目录路径',
                       default=get_default_config_dir())
    
    subparsers = parser.add_subparsers(dest='command', help='命令')
    
    # list命令
    list_parser = subparsers.add_parser('list', help='列出插件')
    list_parser.add_argument('--enabled', action='store_true', 
                            help='只显示已启用的插件')
    
    # install命令
    install_parser = subparsers.add_parser('install', help='安装插件')
    install_parser.add_argument('plugin_file', help='插件包文件路径')
    install_parser.add_argument('--force', action='store_true',
                               help='强制安装（覆盖已有插件）')
    
    # uninstall命令
    uninstall_parser = subparsers.add_parser('uninstall', help='卸载插件')
    uninstall_parser.add_argument('plugin_name', help='插件名称')
    
    # enable命令
    enable_parser = subparsers.add_parser('enable', help='启用插件')
    enable_parser.add_argument('plugin_name', help='插件名称')
    
    # disable命令
    disable_parser = subparsers.add_parser('disable', help='禁用插件')
    disable_parser.add_argument('plugin_name', help='插件名称')
    
    # info命令
    info_parser = subparsers.add_parser('info', help='显示插件信息')
    info_parser.add_argument('plugin_name', help='插件名称')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    # 初始化插件管理器
    config_dir = Path(args.config_dir)
    plugins_dir = config_dir / 'plugins'
    
    plugin_manager = PluginManager(
        plugins_dir=str(plugins_dir),
        config_dir=str(config_dir)
    )
    
    # 执行命令
    if args.command == 'list':
        list_plugins(plugin_manager, args.enabled)
    
    elif args.command == 'install':
        install_plugin(plugin_manager, args.plugin_file, args.force)
    
    elif args.command == 'uninstall':
        uninstall_plugin(plugin_manager, args.plugin_name)
    
    elif args.command == 'enable':
        enable_plugin(plugin_manager, args.plugin_name)
    
    elif args.command == 'disable':
        disable_plugin(plugin_manager, args.plugin_name)
    
    elif args.command == 'info':
        show_plugin_info(plugin_manager, args.plugin_name)


if __name__ == '__main__':
    main()
