#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试服务器修复是否成功
验证run_server函数是否可以正确导入和使用
"""

import os
import sys
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== 测试服务器修复 ===")
print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("\n1. 尝试导入run_server函数...")

try:
    # 尝试导入run_server函数
    from server.server import run_server
    print("✓ 成功导入run_server函数！")
    
    # 检查函数是否存在且可调用
    if callable(run_server):
        print(f"✓ run_server是可调用函数")
        print(f"  函数签名: {run_server.__name__}")
        if run_server.__doc__:
            print(f"  文档字符串: {run_server.__doc__.splitlines()[0].strip()}")
    
    print("\n2. 尝试导入Flask应用...")
    from server.server import app
    print(f"✓ 成功导入Flask应用")
    print(f"  Flask应用名称: {app.name}")
    
    print("\n3. 检查应用路由...")
    routes = []
    for rule in app.url_map.iter_rules():
        methods = ', '.join(sorted(rule.methods))
        routes.append((rule.endpoint, methods, rule.rule))
    
    if routes:
        print(f"✓ 发现{len(routes)}个可用路由:")
        for endpoint, methods, rule in sorted(routes):
            print(f"  - {rule} [{methods}] -> {endpoint}")
    else:
        print("✗ 没有发现路由")
    
    print("\n4. 验证服务器基本功能...")
    # 测试服务器是否可以正常启动（不实际启动，仅验证配置）
    # 检查服务器配置
    if hasattr(app, 'config'):
        print(f"✓ 应用配置存在")
        # 显示一些基本配置
        print(f"  DEBUG模式: {app.config.get('DEBUG')}")
    
    print("\n=== 测试完成 ===")
    print("\n修复总结:")
    print("- 问题原因: server.py中缺少run_server函数，但main.py尝试导入它")
    print("- 解决方案: 在server.py中添加了run_server函数")
    print("- 修复结果: 现在可以成功导入run_server函数")
    print("\n下一步操作:")
    print("1. 运行 python main.py 测试完整系统是否正常工作")
    print("2. 或运行 python main.py --server 单独测试服务端")
    
except ImportError as e:
    print(f"✗ 导入错误: {str(e)}")
    import traceback
    traceback.print_exc()
    print("\n修复失败: 仍然无法导入run_server函数")
    print("请检查server.py文件中是否正确添加了run_server函数")

except Exception as e:
    print(f"✗ 测试过程中发生错误: {str(e)}")
    import traceback
    traceback.print_exc()