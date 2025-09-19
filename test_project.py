#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
项目测试脚本
用于验证项目结构和基本功能
"""

import os
import sys
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

print("=== AI智能体爬虫项目测试 ===")
print(f"当前工作目录: {os.getcwd()}")
print(f"Python版本: {sys.version}")
print("\n1. 检查项目目录结构...")

def check_directory_structure():
    """检查项目目录结构是否正确"""
    required_dirs = ['agent', 'crawler', 'server', 'client', 'utils']
    required_files = ['main.py', 'requirements.txt', 'README.md']
    
    missing = []
    
    # 检查目录
    for dir_name in required_dirs:
        if not os.path.isdir(dir_name):
            missing.append(f"目录: {dir_name}")
    
    # 检查文件
    for file_name in required_files:
        if not os.path.isfile(file_name):
            missing.append(f"文件: {file_name}")
    
    if missing:
        print(f"发现问题: 缺少以下项目组件")
        for item in missing:
            print(f"- {item}")
        return False
    else:
        print("项目目录结构检查通过!")
        return True

print("\n2. 尝试导入核心模块...")

def test_imports():
    """尝试导入项目的核心模块"""
    modules = [
        ('utils.logger', 'setup_logger'),
        ('utils.file_utils', 'save_crawl_results'),
        ('agent.ai_model', 'AIModel'),
        ('crawler.web_crawler', 'WebCrawler'),
        ('server.server', 'app'),
        ('client.gui', None)
    ]
    
    success_count = 0
    fail_count = 0
    
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[''])
            if class_name and not hasattr(module, class_name):
                print(f"✗ 导入 {module_name} 成功，但未找到 {class_name} 类")
                fail_count += 1
            else:
                print(f"✓ 导入 {module_name} 成功")
                success_count += 1
        except ImportError as e:
            print(f"✗ 导入 {module_name} 失败: {str(e)}")
            fail_count += 1
    
    print(f"\n导入测试结果: {success_count} 成功, {fail_count} 失败")
    return success_count > 0

print("\n3. 检查关键配置...")

def check_configs():
    """检查关键配置"""
    # 检查requirements.txt
    if os.path.isfile('requirements.txt'):
        with open('requirements.txt', 'r', encoding='utf-8') as f:
            content = f.read()
            print(f"requirements.txt 包含 {len(content.splitlines())} 行配置")
            
            # 检查关键依赖
            key_packages = ['requests', 'beautifulsoup4', 'selenium', 'PyQt5', 'flask']
            for package in key_packages:
                if package.lower() in content.lower():
                    print(f"✓ 检测到 {package}")
                else:
                    print(f"✗ 未检测到 {package}")
    else:
        print("✗ requirements.txt 不存在")

if __name__ == '__main__':
    # 执行测试
    dir_check = check_directory_structure()
    import_check = test_imports()
    check_configs()
    
    print("\n=== 测试完成 ===")
    print("\n项目状态总结:")
    print(f"- 目录结构: {'正常' if dir_check else '存在问题'}")
    print(f"- 模块导入: {'部分成功' if import_check else '全部失败'}")
    print("\n后续建议:")
    print("1. 如果依赖安装失败，尝试使用国内镜像源重新安装:")
    print("   pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
    print("2. 对于大模型相关依赖，可能需要单独安装:")
    print("   pip install open_clip_torch transformers -i https://pypi.tuna.tsinghua.edu.cn/simple")
    print("3. 安装完成后，运行 main.py 启动程序")
    print("   python main.py")