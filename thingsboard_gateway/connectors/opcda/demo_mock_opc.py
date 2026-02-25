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
Mock OPC 演示脚本

这个脚本演示如何使用 Mock OpenOPC 客户端来模拟 OPC DA 操作。
适用于在 macOS/Linux 上开发和测试，无需真实的 OPC DA 服务器。

这是你原始测试代码的 Mock 版本:
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

使用方法:
    python demo_mock_opc.py
"""

import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from thingsboard_gateway.connectors.opcda import mock_openopc as OpenOPC
except ImportError as e:
    print(f"❌ 无法导入 mock_openopc: {e}")
    print("\n请确保:")
    print("  1. 你在项目根目录运行此脚本")
    print("  2. 或者从正确的位置运行")
    print("\n示例:")
    print("  cd /path/to/thingsboard-gateway")
    print("  python thingsboard_gateway/connectors/opcda/demo_mock_opc.py")
    sys.exit(1)


def print_separator(char="=", length=70):
    """打印分隔符"""
    print(char * length)


def print_section(title):
    """打印节标题"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print("="*70)


def demo_basic_operations():
    """演示基本操作"""
    print_section("演示 1: 基本操作 (你的原始代码)")
    
    print("\n# 创建客户端")
    opc = OpenOPC.client()
    print("✓ OPC 客户端创建成功")
    
    print("\n# 连接到服务器")
    opc.connect('Matrikon.OPC.Simulation.1')
    print("✓ 已连接到 Matrikon.OPC.Simulation.1 (模拟)")
    
    print("\n# 列出所有标签")
    tags = opc.list()
    print(f"✓ 找到 {len(tags)} 个标签")
    print(f"\n前 10 个标签:")
    for i, tag in enumerate(tags[:10], 1):
        print(f"  {i}. {tag}")
    
    print("\n# 读取一个标签")
    tag_name, value, quality, timestamp = opc.read('Random.Int4')
    print(f"✓ Random.Int4 读取成功:")
    print(f"  标签: {tag_name}")
    print(f"  值: {value}")
    print(f"  质量: {quality}")
    print(f"  时间戳: {timestamp}")
    
    print("\n# 关闭连接")
    opc.close()
    print("✓ 连接已关闭")


def demo_multiple_reads():
    """演示批量读取"""
    print_section("演示 2: 批量读取标签")
    
    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')
    
    # 读取多个标签
    tags_to_read = [
        'Random.Int4',
        'Random.Real8',
        'Random.Boolean',
        'Random.String',
        'Bucket.Brigade.Real4',
    ]
    
    print(f"\n读取 {len(tags_to_read)} 个标签...")
    results = opc.read(tags_to_read)
    
    print("\n结果:")
    for tag_name, value, quality, timestamp in results:
        print(f"  {tag_name:<30} = {value:<15} (质量: {quality})")
    
    opc.close()


def demo_write_operations():
    """演示写入操作"""
    print_section("演示 3: 写入标签值")
    
    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')
    
    # 写入单个标签
    print("\n# 写入单个标签")
    tag = 'Random.Int4'
    value = 42
    result = opc.write((tag, value))
    print(f"✓ 写入 {tag} = {value}")
    print(f"  结果: {result}")
    
    # 读取回写的值
    print("\n# 读取回写的值")
    tag_name, read_value, quality, timestamp = opc.read(tag)
    print(f"✓ 读取 {tag_name} = {read_value}")
    
    # 批量写入
    print("\n# 批量写入")
    writes = [
        ('Bucket.Brigade.Real8', 100.5),
        ('Bucket.Brigade.Int4', 999),
    ]
    results = opc.write(writes)
    for tag, status in results:
        print(f"  {tag}: {status}")
    
    opc.close()


def demo_server_info():
    """演示服务器信息"""
    print_section("演示 4: 获取服务器信息")
    
    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')
    
    print("\n# 服务器信息")
    info = opc.info()
    for key, value in info:
        print(f"  {key:<20}: {value}")
    
    opc.close()


def demo_pattern_matching():
    """演示模式匹配"""
    print_section("演示 5: 模式匹配标签")
    
    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')
    
    patterns = [
        'Random.*',
        'Bucket.Brigade.*',
        'Triangle Waves.*',
    ]
    
    for pattern in patterns:
        tags = opc.list(pattern)
        print(f"\n# 模式: '{pattern}' - 找到 {len(tags)} 个标签")
        for tag in tags[:5]:
            print(f"  - {tag}")
        if len(tags) > 5:
            print(f"  ... 还有 {len(tags) - 5} 个")
    
    opc.close()


def demo_dynamic_data():
    """演示动态数据生成"""
    print_section("演示 6: 动态数据 (波形)")
    
    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')
    
    print("\n# 读取波形数据 (10 次)")
    print("这些标签生成动态的波形数据:\n")
    
    wave_tags = [
        'Triangle Waves.Real8',  # 正弦波
        'Saw-toothed Waves.Real8',  # 锯齿波
        'Square Waves.Boolean',  # 方波
    ]
    
    for i in range(10):
        print(f"读取 #{i+1}:")
        for tag in wave_tags:
            _, value, _, _ = opc.read(tag)
            if isinstance(value, bool):
                value_str = "True " if value else "False"
            else:
                value_str = f"{value:6.2f}"
            print(f"  {tag:<30} = {value_str}")
        time.sleep(0.5)
    
    opc.close()


def demo_custom_tags():
    """演示自定义标签"""
    print_section("演示 7: 添加自定义模拟标签")
    
    opc = OpenOPC.client()
    opc.connect('Matrikon.OPC.Simulation.1')
    
    print("\n# 添加自定义标签")
    
    # 添加自定义标签
    import random
    opc.add_mock_tag('Custom.Temperature', lambda: 20 + random.uniform(-5, 5))
    opc.add_mock_tag('Custom.Humidity', lambda: 50 + random.uniform(-10, 10))
    opc.add_mock_tag('Custom.Pressure', lambda: 1013 + random.uniform(-50, 50))
    
    print("✓ 添加了 3 个自定义标签")
    
    # 列出自定义标签
    print("\n# 列出自定义标签")
    custom_tags = opc.list('Custom.*')
    print(f"找到 {len(custom_tags)} 个自定义标签:")
    for tag in custom_tags:
        print(f"  - {tag}")
    
    # 读取自定义标签
    print("\n# 读取自定义标签值")
    for tag in custom_tags:
        _, value, _, _ = opc.read(tag)
        print(f"  {tag:<25} = {value:.2f}")
    
    opc.close()


def main():
    """主函数"""
    print_separator()
    print("  Mock OpenOPC 演示程序")
    print("  模拟你的原始 OPC DA 测试代码")
    print_separator()
    
    print("\n这个演示将展示:")
    print("  1. 基本操作 (你的原始代码)")
    print("  2. 批量读取标签")
    print("  3. 写入标签值")
    print("  4. 获取服务器信息")
    print("  5. 模式匹配标签")
    print("  6. 动态数据生成")
    print("  7. 添加自定义标签")
    
    input("\n按 Enter 键开始...")
    
    try:
        # 运行所有演示
        demo_basic_operations()
        input("\n按 Enter 继续下一个演示...")
        
        demo_multiple_reads()
        input("\n按 Enter 继续下一个演示...")
        
        demo_write_operations()
        input("\n按 Enter 继续下一个演示...")
        
        demo_server_info()
        input("\n按 Enter 继续下一个演示...")
        
        demo_pattern_matching()
        input("\n按 Enter 继续下一个演示...")
        
        demo_dynamic_data()
        input("\n按 Enter 继续最后一个演示...")
        
        demo_custom_tags()
        
    except KeyboardInterrupt:
        print("\n\n演示已取消")
        return
    except Exception as e:
        print(f"\n\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        return
    
    print_section("演示完成!")
    
    print("\n✅ 你已经学会了:")
    print("  - 如何使用 Mock OpenOPC 客户端")
    print("  - 如何在 macOS/Linux 上测试 OPC DA 代码")
    print("  - 如何配置 ThingsBoard Gateway 使用 Mock 模式")
    
    print("\n📚 下一步:")
    print("  1. 在 ThingsBoard Gateway 配置中设置 'useMockOpc: true'")
    print("  2. 查看 opcda_mock_config.json 配置示例")
    print("  3. 如需真实连接，参考 PLATFORM_GUIDE.md")
    
    print("\n" + "="*70)


if __name__ == "__main__":
    main()
