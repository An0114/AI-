#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
最小化测试服务器
用于调试服务器基本功能
"""

import os
import sys
import json
import logging
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

# 设置日志
def setup_logger(name, log_file=None):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    if not logger.handlers:
        # 创建控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 创建格式化器
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_handler.setFormatter(formatter)
        
        # 添加处理器
        logger.addHandler(console_handler)
        
        # 如果提供了日志文件，添加文件处理器
        if log_file:
            try:
                file_handler = logging.FileHandler(log_file)
                file_handler.setLevel(logging.INFO)
                file_handler.setFormatter(formatter)
                logger.addHandler(file_handler)
            except Exception as e:
                logger.warning(f"无法创建日志文件: {str(e)}")
    
    return logger

# 初始化日志
service_logger = setup_logger('minimal_server')

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 记录应用启动时间
app.start_time = time.time()

@app.route('/api/ping', methods=['GET'])
def ping():
    """简单的心跳检测接口"""
    try:
        service_logger.info("收到ping请求")
        return jsonify({
            'status': 'ok', 
            'message': 'Server is running',
            'time': time.time()
        })
    except Exception as e:
        service_logger.error(f"处理ping请求时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/test', methods=['GET'])
def test():
    """简单的测试接口"""
    try:
        service_logger.info("收到test请求")
        return jsonify({
            'status': 'success',
            'data': {
                'test': '成功',
                'timestamp': time.time()
            }
        })
    except Exception as e:
        service_logger.error(f"处理test请求时出错: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/test-post', methods=['POST'])
def test_post():
    """测试POST请求的接口"""
    try:
        service_logger.info("收到test-post请求")
        
        if request.is_json:
            data = request.get_json()
            service_logger.info(f"收到JSON数据: {data}")
            return jsonify({
                'status': 'success',
                'received_data': data
            })
        else:
            return jsonify({'status': 'error', 'message': '请求必须是JSON格式'}), 400
            
    except Exception as e:
        service_logger.error(f"处理test-post请求时出错: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    service_logger.info("启动最小化测试服务器...")
    try:
        # 使用端口8000代替5000，避免端口冲突
        app.run(host='127.0.0.1', port=8000, debug=True)
    except KeyboardInterrupt:
        service_logger.info("服务器已被用户中断")
    except Exception as e:
        service_logger.error(f"服务器异常退出: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        print(f"错误: {str(e)}")
        sys.exit(1)