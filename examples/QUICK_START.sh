#!/bin/bash
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

# 插件系统快速开始脚本

set -e

echo "==================================="
echo "ThingsBoard Gateway 插件系统"
echo "快速开始演示"
echo "==================================="
echo ""

# 获取项目根目录
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_ROOT"

# 步骤1: 检查依赖
echo "步骤 1: 检查依赖..."
python3 -c "import packaging" 2>/dev/null || {
    echo "安装 packaging..."
    pip install packaging
}

echo "✓ 依赖检查完成"
echo ""

# 步骤2: 打包示例插件
echo "步骤 2: 打包示例插件..."
python3 thingsboard_gateway/tools/plugin_packager.py \
    examples/example_plugin \
    -o example_connector_plugin.zip \
    -t example \
    -v 1.0.0 \
    -d "Example connector for demonstration" \
    -a "ThingsBoard Team"

echo "✓ 插件打包完成: example_connector_plugin.zip"
echo ""

# 步骤3: 安装插件
echo "步骤 3: 安装示例插件..."
python3 thingsboard_gateway/tools/plugin_installer.py install example_connector_plugin.zip

echo "✓ 插件安装完成"
echo ""

# 步骤4: 列出插件
echo "步骤 4: 列出已安装的插件..."
python3 thingsboard_gateway/tools/plugin_installer.py list

echo ""

# 步骤5: 显示插件详情
echo "步骤 5: 显示插件详细信息..."
python3 thingsboard_gateway/tools/plugin_installer.py info example_connector_plugin

echo ""
echo "==================================="
echo "✓ 快速开始完成！"
echo "==================================="
echo ""
echo "接下来您可以："
echo "1. 查看插件信息："
echo "   python3 thingsboard_gateway/tools/plugin_installer.py info example_connector_plugin"
echo ""
echo "2. 在网关配置中使用插件："
echo "   添加以下配置到 config/tb_gateway.json:"
echo '   {'
echo '     "connectors": ['
echo '       {'
echo '         "name": "Example Connector",'
echo '         "type": "example",'
echo '         "configuration": "example.json"'
echo '       }'
echo '     ]'
echo '   }'
echo ""
echo "3. 启动REST API服务（如果网关正在运行）："
echo "   访问 http://localhost:9001/api/plugins"
echo ""
echo "4. 创建自己的插件："
echo "   参考 examples/example_plugin/ 和 PLUGIN_SYSTEM_GUIDE.md"
echo ""

# 清理
rm -f example_connector_plugin.zip

echo "完成！"
