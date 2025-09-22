#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试爬取功能和AI总结功能
此脚本用于验证修复后的crawl接口是否能正确爬取网页内容并在启用AI时生成总结
"""

import requests
import time
import json
import logging
import os

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 服务器基础URL
BASE_URL = "http://127.0.0.1:5000"

# 测试的URL列表（使用一些常见的可爬取网站或本地测试网站）
TEST_URLS = [
    "http://example.com",  # 经典测试网站，允许爬虫
    "https://httpbin.org/html",  # 提供测试HTML内容的网站
]

# 测试深度
TEST_DEPTH = 1


def test_crawl_without_ai(url):
    """测试不带AI总结的爬取功能"""
    logger.info(f"开始测试不带AI的爬取功能: {url}")
    
    endpoint = f"{BASE_URL}/api/crawl"
    payload = {
        "url": url,
        "depth": TEST_DEPTH,
        "use_ai": False
    }
    
    try:
        # 发送请求并记录时间
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=60)
        end_time = time.time()
        
        # 检查响应状态
        if response.status_code != 200:
            logger.error(f"爬取请求失败，状态码: {response.status_code}")
            return False
        
        # 解析响应内容
        result = response.json()
        
        # 打印响应内容以调试
        logger.debug(f"爬取响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 检查响应结构
        if "status" not in result or result["status"] != "success":
            logger.error(f"响应状态错误: {result}")
            return False
        
        # 获取数据部分
        data = result.get("data", {})
        
        # 检查是否是模拟结果
        is_mock = data.get("is_mock", True)
        logger.info(f"是否为模拟结果: {is_mock}")
        
        # 检查爬取结果是否包含页面信息
        if is_mock:
            # 如果是模拟结果，检查基本字段
            if "content" not in data:
                logger.error("模拟结果中缺少content字段")
                return False
            if "images" not in data:
                logger.error("模拟结果中缺少images字段")
                return False
            if "links" not in data:
                logger.error("模拟结果中缺少links字段")
                return False
            
            logger.info(f"模拟结果测试通过，内容长度: {len(data['content'])}")
            logger.info(f"模拟图片数量: {len(data['images'])}")
            logger.info(f"模拟链接数量: {len(data['links'])}")
        else:
            # 如果是真实结果，检查pages字段和详细信息
            if "pages" not in data or not isinstance(data["pages"], list):
                logger.error("真实结果中缺少pages字段")
                return False
            
            if len(data["pages"]) == 0:
                logger.warning("爬取结果中没有页面数据")
                # 如果没有页面数据，检查是否有提示信息
                if "message" in data:
                    logger.info(f"提示信息: {data['message']}")
            else:
                # 检查第一个页面的详细信息
                first_page = data["pages"][0]
                page_url = first_page.get("url", "")
                
                # 检查页面基本信息
                required_fields = ["title", "text", "images", "links"]
                missing_fields = [field for field in required_fields if field not in first_page]
                
                if missing_fields:
                    logger.error(f"页面信息缺少字段: {missing_fields}")
                    return False
                
                logger.info(f"成功爬取页面: {page_url}")
                logger.info(f"页面标题: {first_page['title']}")
                logger.info(f"文本长度: {len(first_page['text'])}")
                logger.info(f"图片数量: {len(first_page['images'])}")
                logger.info(f"链接数量: {len(first_page['links'])}")
        
        # 检查统计信息
        if "stats" in data:
            stats = data["stats"]
            logger.info(f"爬取统计: 成功 {stats.get('success_count', 0)}, 失败 {stats.get('error_count', 0)}")
        
        # 记录请求耗时
        logger.info(f"爬取请求耗时: {end_time - start_time:.2f}秒")
        
        return True
        
    except requests.exceptions.Timeout:
        logger.error("爬取请求超时")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("连接服务器失败，请确保服务器正在运行")
        return False
    except Exception as e:
        logger.error(f"爬取测试过程中发生错误: {str(e)}")
        return False


def test_crawl_with_ai(url):
    """测试带AI总结的爬取功能"""
    logger.info(f"开始测试带AI的爬取功能: {url}")
    
    endpoint = f"{BASE_URL}/api/crawl"
    payload = {
        "url": url,
        "depth": TEST_DEPTH,
        "use_ai": True
    }
    
    try:
        # 发送请求并记录时间
        start_time = time.time()
        response = requests.post(endpoint, json=payload, timeout=120)  # 带AI的请求可能需要更长时间
        end_time = time.time()
        
        # 检查响应状态
        if response.status_code != 200:
            logger.error(f"带AI的爬取请求失败，状态码: {response.status_code}")
            return False
        
        # 解析响应内容
        result = response.json()
        
        # 打印响应内容以调试
        logger.debug(f"带AI的爬取响应: {json.dumps(result, ensure_ascii=False, indent=2)}")
        
        # 检查响应结构
        if "status" not in result or result["status"] != "success":
            logger.error(f"响应状态错误: {result}")
            return False
        
        # 获取数据部分
        data = result.get("data", {})
        
        # 检查是否是模拟结果
        is_mock = data.get("is_mock", True)
        logger.info(f"是否为模拟结果: {is_mock}")
        
        # 检查AI总结功能
        ai_summary_found = False
        
        if is_mock:
            # 如果是模拟结果，检查summary字段
            if "summary" not in data:
                logger.error("模拟结果中缺少summary字段")
                return False
            
            logger.info(f"模拟AI总结: {data['summary']}")
            ai_summary_found = True
        else:
            # 如果是真实结果，检查每个页面的summary字段
            if "pages" not in data or not isinstance(data["pages"], list):
                logger.error("真实结果中缺少pages字段")
                return False
            
            for page in data["pages"]:
                if "summary" in page:
                    logger.info(f"页面 {page.get('url', 'unknown')} 的AI总结长度: {len(page['summary'])}")
                    ai_summary_found = True
                    
                    # 检查总结统计信息
                    if "summary_stats" in page:
                        stats = page["summary_stats"]
                        logger.info(f"总结统计: 原文长度 {stats.get('original_length', 0)}, 总结长度 {stats.get('summary_length', 0)}")
                    
                    # 只显示第一个页面的总结内容
                    if len(page['summary']) > 100:
                        logger.info(f"总结内容预览: {page['summary'][:100]}...")
                    else:
                        logger.info(f"总结内容: {page['summary']}")
                    
                    break  # 只检查第一个页面的总结
        
        # 验证是否找到了AI总结
        if not ai_summary_found:
            logger.error("未找到AI总结结果")
            return False
        
        # 记录请求耗时
        logger.info(f"带AI的爬取请求耗时: {end_time - start_time:.2f}秒")
        
        return True
        
    except requests.exceptions.Timeout:
        logger.error("带AI的爬取请求超时")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("连接服务器失败，请确保服务器正在运行")
        return False
    except Exception as e:
        logger.error(f"带AI的爬取测试过程中发生错误: {str(e)}")
        return False


def run_all_tests():
    """运行所有测试"""
    logger.info("======= 开始爬取功能和AI总结功能测试 =======")
    
    # 检查服务器是否正在运行
    try:
        response = requests.get(f"{BASE_URL}/api/ping", timeout=5)
        if response.status_code != 200:
            logger.error("服务器未正常运行")
            logger.info("请先启动服务器: python server/server.py")
            return
    except requests.exceptions.ConnectionError:
        logger.error("无法连接到服务器")
        logger.info("请先启动服务器: python server/server.py")
        return
    
    # 初始化测试结果
    results = {
        "total": 0,
        "passed": 0,
        "failed": 0
    }
    
    # 对每个URL运行测试
    for url in TEST_URLS:
        # 测试不带AI的爬取
        results["total"] += 1
        logger.info(f"\n--- 测试 {results['total']}: 不带AI爬取 {url} ---")
        if test_crawl_without_ai(url):
            results["passed"] += 1
            logger.info("✅ 测试通过")
        else:
            results["failed"] += 1
            logger.info("❌ 测试失败")
        
        # 测试带AI的爬取
        results["total"] += 1
        logger.info(f"\n--- 测试 {results['total']}: 带AI爬取 {url} ---")
        if test_crawl_with_ai(url):
            results["passed"] += 1
            logger.info("✅ 测试通过")
        else:
            results["failed"] += 1
            logger.info("❌ 测试失败")
        
        # 在两次测试之间添加短暂延迟
        time.sleep(2)
    
    # 打印测试总结
    logger.info("\n======= 测试总结 =======")
    logger.info(f"总测试数: {results['total']}")
    logger.info(f"通过数: {results['passed']}")
    logger.info(f"失败数: {results['failed']}")
    logger.info(f"通过率: {results['passed'] / results['total'] * 100:.1f}%" if results['total'] > 0 else "无测试运行")
    
    if results['failed'] == 0:
        logger.info("🎉 所有测试通过")
    else:
        logger.info("⚠️ 部分测试失败，请检查日志获取详细信息")


if __name__ == "__main__":
    run_all_tests()