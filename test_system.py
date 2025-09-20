#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
系统功能测试脚本
"""

import os
import sys
import time
import requests

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

SERVER_URL = "http://localhost:5000/api"

print("=== 系统功能测试 ===")
print(f"测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

# 测试ping接口
def test_ping():
    """测试服务端是否在线"""
    print("\n1. 测试服务端ping接口...")
    try:
        response = requests.get(f"{SERVER_URL}/ping", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 服务端在线: {data.get('message')}")
            print(f"  版本: {data.get('version')}")
            print(f"  运行时间: {data.get('uptime_seconds')} 秒")
            return True
        else:
            print(f"✗ 服务端响应错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 无法连接到服务端: {str(e)}")
        return False

# 测试models接口
def test_models():
    """测试可用模型列表"""
    print("\n2. 测试models接口...")
    try:
        response = requests.get(f"{SERVER_URL}/models", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 模型列表获取成功")
            print(f"  总模型数: {data.get('total_models')}")
            print(f"  可用模型: {data.get('data')}")
            return True
        else:
            print(f"✗ 模型列表获取失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 模型列表请求异常: {str(e)}")
        return False

# 测试分析接口
def test_analyze():
    """测试分析接口"""
    print("\n3. 测试analyze接口...")
    try:
        test_data = {
            "content": {
                "text": ["一只猫", "一只狗", "一辆汽车"],
                "image": "https://example.com/image.jpg"
            },
            "model_type": "clip",
            "task": "classification"
        }
        
        response = requests.post(
            f"{SERVER_URL}/analyze",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 分析请求成功")
            print(f"  状态: {data.get('status')}")
            print(f"  分析结果: {data.get('data')}")
            return True
        else:
            print(f"✗ 分析请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 分析请求异常: {str(e)}")
        return False

# 测试爬取接口
def test_crawl():
    """测试爬取接口"""
    print("\n4. 测试crawl接口...")
    try:
        test_data = {
            "url": "https://example.com",
            "depth": 1,
            "use_ai": False
        }
        
        response = requests.post(
            f"{SERVER_URL}/crawl",
            json=test_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✓ 爬取请求成功")
            print(f"  状态: {data.get('status')}")
            print(f"  爬取页面数: {data.get('data', {}).get('total_pages')}")
            return True
        else:
            print(f"✗ 爬取请求失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ 爬取请求异常: {str(e)}")
        return False

# 主测试函数
def main():
    """运行所有测试"""
    tests = [
        test_ping,
        test_models,
        test_analyze,
        test_crawl
    ]
    
    success_count = 0
    
    for test_func in tests:
        if test_func():
            success_count += 1
    
    print("\n=== 测试结果汇总 ===")
    print(f"总测试数: {len(tests)}")
    print(f"通过测试数: {success_count}")
    print(f"失败测试数: {len(tests) - success_count}")
    
    if success_count == len(tests):
        print("✓ 恭喜! 所有测试通过。系统功能正常。")
    else:
        print("✗ 部分测试未通过，请检查错误日志并修复问题。")

if __name__ == "__main__":
    main()
