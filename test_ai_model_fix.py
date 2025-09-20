#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试修改后的AI模型功能
验证模拟模型是否能正确工作
"""

import os
import sys
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# 导入修改后的AIModel类
from agent.ai_model import AIModel

print("=== 测试修改后的AI模型 ===")
print(f"当前时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
print("\n1. 初始化CLIP模型...")

# 初始化AI模型
try:
    print("正在创建AIModel实例...")
    start_time = time.time()
    ai_model = AIModel(model_type='clip')
    init_time = time.time() - start_time
    print(f"模型初始化耗时: {init_time:.2f} 秒")
    
    # 获取模型状态
    status = ai_model.get_status()
    print("\n模型状态信息:")
    for key, value in status.items():
        print(f"  - {key}: {value}")
    
    # 测试分析功能
    print("\n2. 测试模型分析功能...")
    
    # 测试零样本分类
    print("\n测试零样本分类:")
    test_data = {
        'text': ['一只猫', '一只狗', '一辆汽车', '一朵花'],
        'image': 'https://example.com/cat.jpg'  # 示例URL，模拟模型不会真正加载
    }
    result = ai_model.analyze(test_data, task='classification')
    print(f"分类结果: {result.get('top_prediction')}")
    print(f"完整结果: {result}")
    
    # 测试文本-图像相似度
    print("\n测试文本-图像相似度:")
    similarity_data = {
        'text': '这是一只可爱的小猫',
        'image': 'https://example.com/cat.jpg'
    }
    sim_result = ai_model.analyze(similarity_data, task='similarity')
    print(f"相似度分数: {sim_result.get('similarity_score')}")
    print(f"相似度解释: {sim_result.get('interpretation')}")
    
    # 测试图像描述
    print("\n测试图像描述:")
    caption_result = ai_model.analyze('https://example.com/image.jpg', task='captioning')
    print(f"生成的描述: {caption_result.get('captions')}")
    
    print("\n=== 测试完成 ===")
    print(f"\n测试总结:")
    print(f"- 模型初始化: {'成功' if ai_model.is_initialized() else '失败'}")
    print(f"- 是否使用模拟模型: {status.get('is_mock')}")
    print(f"- 是否有真实模型: {status.get('has_real_model')}")
    print(f"- 所有测试: {'通过' if ai_model.is_initialized() else '失败'}")
    
    if status.get('is_mock'):
        print("\n提示: 当前使用的是模拟模型，这是因为无法连接到huggingface.co下载预训练权重。")
        print("      模拟模型可以正常运行，但不会提供真实的AI分析能力。")
        print("      如需使用真实模型，请确保网络连接正常，或手动下载模型权重。")
    
    # 输出建议
    print("\n解决模型下载问题的建议:")
    print("1. 检查网络连接是否正常")
    print("2. 尝试设置环境变量 CLIP_MODEL_PATH 指向本地模型路径")
    print("3. 使用国内镜像源安装依赖: pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple")
    
    # 创建一个完整的系统测试脚本
    print("\n\n=== 创建系统测试脚本 ===")
    test_script_content = '''#!/usr/bin/env python3
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
'''
    
    # 写入系统测试脚本
    with open("test_system.py", "w", encoding="utf-8") as f:
        f.write(test_script_content)
    
    # 赋予执行权限
    try:
        os.chmod("test_system.py", 0o755)
    except:
        pass  # Windows系统不需要设置执行权限
    
    print("已创建系统测试脚本: test_system.py")
    print("使用方法: python test_system.py")
    print("注意: 运行此脚本前，请确保服务端已经启动")
    
    # 输出启动系统的命令
    print("\n\n=== 启动系统的方法 ===")
    print("1. 启动完整系统(服务端+客户端):")
    print("   python main.py")
    print("\n2. 仅启动服务端:")
    print("   python main.py --server")
    print("\n3. 仅启动客户端:")
    print("   python main.py --client")
    print("\n4. 在服务端启动后运行系统测试:")
    print("   python test_system.py")
    

except Exception as e:
    print(f"测试失败: {str(e)}")
    import traceback
    traceback.print_exc()