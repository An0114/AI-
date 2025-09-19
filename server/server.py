#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI智能体爬虫服务端
提供RESTful API接口，集成CLIP等大模型进行智能分析
"""

import os
import sys
import json
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
import uvicorn

# 导入AI模型和爬虫相关模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agent.ai_model import AIModel
from crawler.web_crawler import WebCrawler
from utils.logger import setup_logger

# 设置日志
service_logger = setup_logger('server', 'server.log')

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 初始化AI模型和爬虫
available_models = {
    'clip': None,
    'transformer': None
}

crawler = None


@app.before_request
def initialize_components():
    """在第一个请求前初始化AI模型和爬虫"""
    global available_models, crawler
    try:
        # 初始化CLIP模型
        available_models['clip'] = AIModel(model_type='clip')
        service_logger.info("CLIP模型初始化成功")
        
        # 初始化爬虫
        crawler = WebCrawler()
        service_logger.info("网络爬虫初始化成功")
        
    except Exception as e:
        service_logger.error(f"组件初始化失败: {str(e)}")


@app.route('/api/ping', methods=['GET'])
def ping():
    """心跳检测接口"""
    return jsonify({'status': 'ok', 'message': 'Server is running'})


@app.route('/api/crawl', methods=['POST'])
def crawl():
    """执行爬虫任务接口"""
    try:
        data = request.json
        url = data.get('url')
        depth = data.get('depth', 1)
        use_ai = data.get('use_ai', False)
        ai_model = data.get('ai_model', 'clip')
        keywords = data.get('keywords', [])
        
        if not url:
            return jsonify({'status': 'error', 'message': 'URL不能为空'}), 400
        
        if not crawler:
            return jsonify({'status': 'error', 'message': '爬虫未初始化'}), 500
        
        # 执行爬取任务
        result = crawler.crawl(
            url=url,
            depth=depth,
            use_ai=use_ai,
            ai_model=available_models.get(ai_model) if use_ai else None,
            keywords=keywords
        )
        
        service_logger.info(f"爬取任务完成: {url}")
        return jsonify({'status': 'success', 'data': result})
        
    except Exception as e:
        service_logger.error(f"爬取任务失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """使用AI模型分析内容接口"""
    try:
        data = request.json
        content = data.get('content')
        model_type = data.get('model_type', 'clip')
        task = data.get('task', 'classification')
        
        if not content:
            return jsonify({'status': 'error', 'message': '内容不能为空'}), 400
        
        model = available_models.get(model_type)
        if not model:
            return jsonify({'status': 'error', 'message': f'模型 {model_type} 未初始化'}), 500
        
        # 使用AI模型进行分析
        result = model.analyze(content, task)
        
        service_logger.info(f"AI分析完成，模型: {model_type}")
        return jsonify({'status': 'success', 'data': result})
        
    except Exception as e:
        service_logger.error(f"AI分析失败: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500


@app.route('/api/models', methods=['GET'])
def list_models():
    """列出可用的AI模型"""
    models_status = {}
    for model_name, model in available_models.items():
        models_status[model_name] = {'available': model is not None}
    
    return jsonify({'status': 'success', 'data': models_status})


def run_server(host='127.0.0.1', port=5000, debug=False):
    """运行服务端
    
    Args:
        host (str): 主机地址
        port (int): 端口号
        debug (bool): 是否开启调试模式
    """
    service_logger.info(f"服务端启动于 {host}:{port}")
    
    # 使用uvicorn作为WSGI服务器运行Flask应用
    uvicorn.run(
        'server.server:app',
        host=host,
        port=port,
        reload=debug,
        log_level='info' if debug else 'warning'
    )


if __name__ == '__main__':
    # 直接运行时使用Flask内置服务器（仅用于开发）
    run_server(debug=True)