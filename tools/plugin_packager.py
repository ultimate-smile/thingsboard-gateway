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
插件打包工具
用于将连接器打包成可安装的插件包
"""

import argparse
import json
import os
import sys
import zipfile
from pathlib import Path


def create_plugin_manifest(connector_type, version, description="", author="", dependencies=None):
    """创建插件清单文件"""
    manifest = {
        "name": f"{connector_type}_connector_plugin",
        "version": version,
        "plugin_type": "connector",
        "connector_type": connector_type,
        "display_name": f"{connector_type.upper()} Connector",
        "description": description or f"{connector_type.upper()} protocol connector plugin",
        "author": author,
        "license": "Apache-2.0",
        "python_requires": ">=3.7",
        "dependencies": dependencies or [],
        "entry_point": f"{connector_type.capitalize()}Connector",
        "module_name": f"{connector_type}_connector",
        "gateway_version": ">=3.0"
    }
    return manifest


def package_connector(source_dir, output_file, manifest_data=None):
    """
    打包连接器为插件
    
    Args:
        source_dir: 源代码目录
        output_file: 输出文件路径
        manifest_data: 插件清单数据
    
    Returns:
        bool: 是否成功
    """
    source_path = Path(source_dir)
    
    if not source_path.exists():
        print(f"错误: 源目录不存在: {source_dir}")
        return False
    
    # 创建临时清单文件
    manifest_file = source_path / "plugin.json"
    manifest_existed = manifest_file.exists()
    
    if manifest_data and not manifest_existed:
        with open(manifest_file, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print(f"创建插件清单: {manifest_file}")
    
    # 创建zip文件
    try:
        with zipfile.ZipFile(output_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for file_path in source_path.rglob('*'):
                if file_path.is_file():
                    # 排除某些文件
                    if any(pattern in str(file_path) for pattern in ['__pycache__', '.pyc', '.pyo', '.git']):
                        continue
                    
                    arcname = file_path.relative_to(source_path)
                    zipf.write(file_path, arcname)
                    print(f"添加文件: {arcname}")
        
        print(f"\n✓ 插件包创建成功: {output_file}")
        return True
    
    except Exception as e:
        print(f"错误: 打包失败: {e}")
        return False
    
    finally:
        # 清理临时创建的清单文件
        if manifest_data and not manifest_existed and manifest_file.exists():
            manifest_file.unlink()


def main():
    parser = argparse.ArgumentParser(description='ThingsBoard Gateway 插件打包工具')
    
    parser.add_argument('source', help='源代码目录')
    parser.add_argument('-o', '--output', help='输出文件路径', required=True)
    parser.add_argument('-t', '--type', help='连接器类型（如opcua, modbus等）', required=True)
    parser.add_argument('-v', '--version', help='插件版本号', default='1.0.0')
    parser.add_argument('-d', '--description', help='插件描述', default='')
    parser.add_argument('-a', '--author', help='作者', default='')
    parser.add_argument('--deps', help='依赖包（逗号分隔）', default='')
    
    args = parser.parse_args()
    
    # 解析依赖
    dependencies = [dep.strip() for dep in args.deps.split(',') if dep.strip()]
    
    # 创建清单
    manifest = create_plugin_manifest(
        connector_type=args.type,
        version=args.version,
        description=args.description,
        author=args.author,
        dependencies=dependencies
    )
    
    print(f"=== 开始打包插件 ===")
    print(f"连接器类型: {args.type}")
    print(f"版本: {args.version}")
    print(f"源目录: {args.source}")
    print(f"输出文件: {args.output}\n")
    
    # 打包
    success = package_connector(args.source, args.output, manifest)
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
