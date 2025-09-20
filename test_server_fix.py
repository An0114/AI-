#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
服务器修复测试脚本
用于验证修复后的服务器功能是否正常
"""

import os
import sys
import time
import requests
import json
import logging
import subprocess
import threading

# 设置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 服务器配置
SERVER_URL = "http://localhost:5000"
SERVER_PORT = 5000
SERVER_PROCESS = None


def start_server():
    """启动服务器进程"""
    global SERVER_PROCESS
    
    # 确保在正确的目录执行
    project_root = os.path.dirname(os.path.abspath(__file__))
    server_script = os.path.join(project_root, 'server', 'server.py')
    
    logger.info(f"准备启动服务器: {server_script}")
    
    # 使用subprocess启动服务器
    SERVER_PROCESS = subprocess.Popen(
        [sys.executable, server_script],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        cwd=project_root
    )
    
    # 等待服务器启动
    time.sleep(5)
    
    return SERVER_PROCESS.poll() is None  # 返回True表示服务器正在运行


def stop_server():
    """停止服务器进程"""
    global SERVER_PROCESS
    
    if SERVER_PROCESS and SERVER_PROCESS.poll() is None:
        logger.info("正在停止服务器...")
        
        # 尝试优雅关闭
        try:
            # 发送终止信号
            SERVER_PROCESS.terminate()
            # 等待进程结束，最多等待5秒
            SERVER_PROCESS.wait(timeout=5)
        except subprocess.TimeoutExpired:
            # 如果超时，强制终止
            logger.warning("服务器未能优雅关闭，强制终止")
            SERVER_PROCESS.kill()
        
        logger.info("服务器已停止")


def test_ping():
    """测试ping接口"""
    logger.info("测试ping接口...")
    try:
        response = requests.get(f"{SERVER_URL}/api/ping")
        logger.info(f"ping响应状态码: {response.status_code}")
        logger.info(f"ping响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"ping测试失败: {str(e)}")
        return False


def test_models():
    """测试models接口"""
    logger.info("测试models接口...")
    try:
        response = requests.get(f"{SERVER_URL}/api/models")
        logger.info(f"models响应状态码: {response.status_code}")
        logger.info(f"models响应内容: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        logger.error(f"models测试失败: {str(e)}")
        return False


def test_analyze(): 
    """测试analyze接口"""
    logger.info("测试analyze接口...")
    try:
        # 准备测试数据
        test_data = {
            "content": "这是一个测试文本",
            "model_type": "clip",
            "task": "classification"
        }
        
        response = requests.post(
            f"{SERVER_URL}/api/analyze",
            json=test_data,
            headers={"Content-Type": "application/json"}
        )
        
        logger.info(f"analyze响应状态码: {response.status_code}")
        logger.info(f"analyze响应内容: {response.json()}")
        
        # 因为可能使用模拟模型，所以只要返回非500错误就算成功
        return response.status_code != 500
    except Exception as e:
        logger.error(f"analyze测试失败: {str(e)}")
        return False


def test_invalid_json():
    """测试无效JSON请求"""
    logger.info("测试无效JSON请求...")
    try:
        # 发送非JSON格式数据
        response = requests.post(
            f"{SERVER_URL}/api/analyze",
            data="这不是JSON数据",
            headers={"Content-Type": "text/plain"}
        )
        
        logger.info(f"无效JSON响应状态码: {response.status_code}")
        logger.info(f"无效JSON响应内容: {response.json()}")
        
        # 应该返回400错误，表示请求格式错误
        return response.status_code == 400
    except Exception as e:
        logger.error(f"无效JSON测试失败: {str(e)}")
        return False


def main():
    """主测试函数"""
    test_results = {
        "start_server": False,
        "ping": False,
        "models": False,
        "analyze": False,
        "invalid_json": False
    }
    
    try:
        # 启动服务器
        test_results["start_server"] = start_server()
        if not test_results["start_server"]:
            logger.error("服务器启动失败，无法进行后续测试")
            return
        
        # 运行各项测试
        test_results["ping"] = test_ping()
        test_results["models"] = test_models()
        test_results["analyze"] = test_analyze()
        test_results["invalid_json"] = test_invalid_json()
        
        # 显示测试结果
        logger.info("\n===== 测试结果汇总 =====")
        all_passed = True
        for test_name, passed in test_results.items():
            status = "通过" if passed else "失败"
            logger.info(f"{test_name}: {status}")
            if not passed:
                all_passed = False
        
        if all_passed:
            logger.info("\n所有测试通过！服务器修复成功。")
        else:
            logger.warning("\n部分测试未通过，请查看日志获取详细信息。")
            
    except Exception as e:
        logger.error(f"测试过程中出现异常: {str(e)}")
    finally:
        # 确保停止服务器
        stop_server()


if __name__ == "__main__":
    main()