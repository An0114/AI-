import requests
import time
import json

# 服务器URL
sERVER_URL = "http://127.0.0.1:5000"


def test_ping():
    """测试ping接口"""
    try:
        response = requests.get(f"{sERVER_URL}/api/ping", timeout=5)
        print(f"ping接口测试结果: 状态码={response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"ping接口测试失败: {str(e)}")
        return False


def test_models():
    """测试models接口"""
    try:
        response = requests.get(f"{sERVER_URL}/api/models", timeout=5)
        print(f"models接口测试结果: 状态码={response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"models接口测试失败: {str(e)}")
        return False


def test_analyze():
    """测试analyze接口"""
    try:
        data = {
            "content": "这是一段测试文本",
            "task": "sentiment"
        }
        response = requests.post(
            f"{sERVER_URL}/api/analyze",
            json=data,
            timeout=5
        )
        print(f"analyze接口测试结果: 状态码={response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"analyze接口测试失败: {str(e)}")
        return False


def test_crawl():
    """测试crawl接口"""
    try:
        data = {
            "url": "https://example.com",
            "depth": 1,
            "use_ai": True
        }
        response = requests.post(
            f"{sERVER_URL}/api/crawl",
            json=data,
            timeout=5
        )
        print(f"crawl接口测试结果: 状态码={response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"crawl接口测试失败: {str(e)}")
        return False


def test_status():
    """测试status接口"""
    try:
        response = requests.get(f"{sERVER_URL}/api/status", timeout=5)
        print(f"status接口测试结果: 状态码={response.status_code}")
        print(f"响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"status接口测试失败: {str(e)}")
        return False


def run_all_tests():
    """运行所有接口测试"""
    print("\n=== 开始测试所有修复后的接口 ===")
    
    tests = [
        ("ping接口", test_ping),
        ("models接口", test_models),
        ("analyze接口", test_analyze),
        ("crawl接口", test_crawl),
        ("status接口", test_status)
    ]
    
    results = []
    passed_count = 0
    
    for name, test_func in tests:
        print(f"\n测试: {name}")
        start_time = time.time()
        success = test_func()
        end_time = time.time()
        
        results.append((name, success, end_time - start_time))
        if success:
            passed_count += 1
            print(f"测试通过，耗时: {end_time - start_time:.2f}秒")
        else:
            print("测试失败")
    
    # 打印总结
    print("\n=== 测试总结 ===")
    print(f"总测试数: {len(tests)}, 通过数: {passed_count}, 失败数: {len(tests) - passed_count}")
    
    for name, success, duration in results:
        status = "✅ 通过" if success else "❌ 失败"
        print(f"{name}: {status} ({duration:.2f}秒)")
    
    if passed_count == len(tests):
        print("\n🎉 所有接口测试通过！")
    else:
        print("\n⚠️ 部分接口测试失败，请检查修复。")


if __name__ == "__main__":
    print("请确保服务器已经在 http://127.0.0.1:5000 启动！")
    print("3秒后开始测试...")
    time.sleep(3)
    run_all_tests()