#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI智能体爬虫服务端 - 简化版
提供RESTful API接口，修复500错误问题
"""

import os
import sys
import json
import logging
import time
from flask import Flask, request, jsonify
from flask_cors import CORS

# 设置基本日志配置
def setup_logger(name, log_file=None):
    """设置日志记录器"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    
    # 清空已有处理器
    if logger.handlers:
        logger.handlers.clear()
    
    # 创建控制台处理器
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    
    # 创建格式化器
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(formatter)
    
    # 添加控制台处理器
    logger.addHandler(console_handler)
    
    # 如果提供了日志文件，添加文件处理器
    if log_file:
        try:
            # 确保日志目录存在
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)
            
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
        except Exception as e:
            logger.warning(f"无法创建日志文件: {str(e)}")
    
    return logger

# 初始化日志
service_logger = setup_logger('server', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'server.log'))

# 初始化Flask应用
app = Flask(__name__)
CORS(app)  # 允许跨域请求

# 记录应用启动时间
app.start_time = time.time()

# 初始化应用状态
available_models = {}
crawler = None
initialized = False

# 尝试导入必要的模块，但即使失败也继续运行
try:
    # 添加项目根目录到路径
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.append(project_root)
        service_logger.info(f"添加项目根目录到路径: {project_root}")
    
    # 尝试导入AI模型和爬虫模块，但提供模拟实现作为后备
    try:
        from agent.ai_model import AIModel
        service_logger.info("成功导入AIModel")
    except Exception as e:
        service_logger.error(f"无法导入AIModel: {str(e)}")
        
        # 定义模拟的AIModel类
        class AIModel:
            def __init__(self, model_type='clip'):
                self.model_type = model_type
                self.initialized = False
                service_logger.warning(f"使用模拟的AIModel，类型: {model_type}")
            
            def analyze(self, content, task='classification'):
                return {
                    'status': 'success',
                    'result': f'模拟分析结果 (任务: {task})',
                    'model_type': self.model_type,
                    'is_mock': True
                }
            
            def is_initialized(self):
                return self.initialized
            
            def get_model_info(self):
                return {'model_type': self.model_type, 'version': 'mock-1.0', 'status': 'available'}
    
    try:
        from crawler.web_crawler import WebCrawler
        service_logger.info("成功导入WebCrawler")
    except Exception as e:
        service_logger.error(f"无法导入WebCrawler: {str(e)}")
        
        # 定义模拟的WebCrawler类
        class WebCrawler:
            def __init__(self):
                service_logger.warning("使用模拟的WebCrawler")
            
            def crawl(self, url, depth=1, use_ai=False, ai_model=None, keywords=[]):
                result = {
                    'status': 'success',
                    'url': url,
                    'depth': depth,
                    'content': '这是模拟的网页内容',
                    'timestamp': time.time(),
                    'is_mock': True,
                    'crawled_pages': 1,
                    'processed_time': 0.1
                }
                
                if use_ai and ai_model:
                    try:
                        result['ai_analysis'] = ai_model.analyze(url)
                    except Exception as e:
                        result['ai_analysis_error'] = str(e)
                
                return result
    
except Exception as e:
    service_logger.critical(f"初始化过程中出现严重错误: {str(e)}")
    import traceback
    service_logger.error(traceback.format_exc())


@app.route('/api/ping', methods=['GET'])
def ping():
    """简单的心跳检测接口，作为健康检查"""
    try:
        service_logger.debug("收到ping请求")
        
        # 检查服务器基本状态
        uptime = int(time.time() - app.start_time) if hasattr(app, 'start_time') else 0
        
        response = {
            'status': 'ok',
            'message': 'Server is running',
            'version': '1.0.0',
            'uptime_seconds': uptime,
            'timestamp': time.time()
        }
        
        service_logger.debug(f"返回ping响应: {response}")
        return jsonify(response)
    except Exception as e:
        service_logger.error(f"处理ping请求时出错: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/api/models', methods=['GET'])
def list_models():
    """列出可用的AI模型"""
    try:
        service_logger.debug("收到list_models请求")
        
        # 确保模型已初始化
        global available_models
        if not available_models:
            try:
                # 初始化CLIP模型（使用模拟或真实模型）
                available_models['clip'] = AIModel(model_type='clip')
                service_logger.info("CLIP模型初始化成功")
            except Exception as e:
                service_logger.error(f"CLIP模型初始化失败: {str(e)}")
        
        # 构建模型状态信息
        models_status = {}
        for model_name, model in available_models.items():
            model_status = {
                'available': model is not None,
                'type': 'real' if model and not hasattr(model, 'is_mock') else 'mock'
            }
            
            # 尝试获取更多模型信息（如果支持）
            if model and hasattr(model, 'get_model_info'):
                try:
                    model_info = model.get_model_info()
                    model_status.update(model_info)
                except Exception as e:
                    service_logger.warning(f"无法获取模型{model_name}的信息: {str(e)}")
            
            models_status[model_name] = model_status
        
        response = {
            'status': 'success',
            'data': models_status,
            'total_models': len(models_status)
        }
        
        service_logger.debug(f"返回models响应: {response}")
        return jsonify(response)
    except Exception as e:
        service_logger.error(f"处理list_models请求时出错: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/api/analyze', methods=['POST'])
def analyze():
    """使用AI模型分析内容接口"""
    try:
        service_logger.debug("收到analyze请求")
        
        # 验证请求数据
        if not request.is_json:
            service_logger.warning("analyze请求不是JSON格式")
            return jsonify({'status': 'error', 'message': 'Request must be JSON format'}), 400
        
        data = request.json
        service_logger.debug(f"analyze请求数据: {data}")
        
        # 提取请求参数
        content = data.get('content')
        model_type = data.get('model_type', 'clip')
        task = data.get('task', 'classification')
        
        # 验证必要参数
        if not content:
            service_logger.warning("analyze请求缺少content参数")
            return jsonify({'status': 'error', 'message': 'Content parameter is required'}), 400
        
        # 确保模型已初始化
        global available_models
        if model_type not in available_models or available_models[model_type] is None:
            try:
                available_models[model_type] = AIModel(model_type=model_type)
                service_logger.info(f"模型{model_type}初始化成功")
            except Exception as e:
                service_logger.error(f"模型{model_type}初始化失败: {str(e)}")
                return jsonify({'status': 'error', 'message': f'Model {model_type} initialization failed'}), 500
        
        # 获取模型
        model = available_models[model_type]
        
        # 使用模型进行分析
        try:
            service_logger.info(f"使用模型{model_type}执行{task}任务")
            result = model.analyze(content, task)
            
            # 确保结果是有效的
            if result is None:
                service_logger.warning(f"模型{model_type}返回空结果")
                return jsonify({'status': 'warning', 'message': 'Analysis returned empty result'}), 200
            
            response = {
                'status': 'success',
                'data': result,
                'model_used': model_type,
                'task_performed': task
            }
            
            service_logger.debug(f"analyze请求成功完成")
            return jsonify(response)
            
        except Exception as analysis_error:
            service_logger.error(f"模型分析过程中出错: {str(analysis_error)}")
            import traceback
            service_logger.error(traceback.format_exc())
            
            # 根据错误类型返回不同的状态码
            if isinstance(analysis_error, ValueError):
                return jsonify({'status': 'error', 'message': f'Invalid parameter: {str(analysis_error)}'}), 400
            else:
                return jsonify({'status': 'error', 'message': f'Analysis failed: {str(analysis_error)}'}), 500
        
    except Exception as e:
        service_logger.error(f"处理analyze请求时出错: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/api/crawl', methods=['POST'])
def crawl():
    """执行爬虫任务接口"""
    try:
        service_logger.debug("收到crawl请求")
        
        # 验证请求数据
        if not request.is_json:
            service_logger.warning("crawl请求不是JSON格式")
            return jsonify({'status': 'error', 'message': 'Request must be JSON format'}), 400
        
        data = request.json
        service_logger.debug(f"crawl请求数据: {data}")
        
        # 提取请求参数
        url = data.get('url')
        depth = data.get('depth', 1)
        use_ai = data.get('use_ai', False)
        ai_model_type = data.get('ai_model', 'clip')
        keywords = data.get('keywords', [])
        
        # 验证必要参数
        if not url:
            service_logger.warning("crawl请求缺少url参数")
            return jsonify({'status': 'error', 'message': 'URL parameter is required'}), 400
        
        # 确保爬虫已初始化
        global crawler
        if crawler is None:
            try:
                crawler = WebCrawler()
                service_logger.info("爬虫初始化成功")
            except Exception as e:
                service_logger.error(f"爬虫初始化失败: {str(e)}")
                return jsonify({'status': 'error', 'message': 'Crawler initialization failed'}), 500
        
        # 准备AI模型（如果需要）
        ai_model = None
        if use_ai:
            try:
                global available_models
                if ai_model_type not in available_models or available_models[ai_model_type] is None:
                    available_models[ai_model_type] = AIModel(model_type=ai_model_type)
                ai_model = available_models[ai_model_type]
                service_logger.info(f"准备使用AI模型: {ai_model_type}")
            except Exception as e:
                service_logger.warning(f"无法准备AI模型: {str(e)}")
                # 即使没有AI模型也继续执行爬取
                use_ai = False
        
        # 执行爬取任务
        try:
            service_logger.info(f"开始爬取URL: {url}, 深度: {depth}")
            result = crawler.crawl(
                url=url,
                depth=depth,
                use_ai=use_ai,
                ai_model=ai_model,
                keywords=keywords
            )
            
            response = {
                'status': 'success',
                'data': result,
                'url': url,
                'depth': depth,
                'used_ai': use_ai
            }
            
            service_logger.debug(f"crawl请求成功完成")
            return jsonify(response)
            
        except Exception as crawl_error:
            service_logger.error(f"爬取过程中出错: {str(crawl_error)}")
            import traceback
            service_logger.error(traceback.format_exc())
            
            # 根据错误类型返回不同的状态码
            if isinstance(crawl_error, ValueError):
                return jsonify({'status': 'error', 'message': f'Invalid parameter: {str(crawl_error)}'}), 400
            elif isinstance(crawl_error, ConnectionError):
                return jsonify({'status': 'error', 'message': f'Connection error: {str(crawl_error)}'}), 503
            else:
                return jsonify({'status': 'error', 'message': f'Crawling failed: {str(crawl_error)}'}), 500
        
    except Exception as e:
        service_logger.error(f"处理crawl请求时出错: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


@app.route('/api/status', methods=['GET'])
def status():
    """获取服务器详细状态"""
    try:
        service_logger.debug("收到status请求")
        
        # 基本信息
        uptime = int(time.time() - app.start_time) if hasattr(app, 'start_time') else 0
        
        # 组件状态
        components = {
            'crawler': crawler is not None,
            'models': {
                'count': len(available_models),
                'available': {name: model is not None for name, model in available_models.items()}
            }
        }
        
        # 系统信息
        system_info = {
            'python_version': sys.version,
            'flask_version': Flask.__version__ if hasattr(Flask, '__version__') else 'unknown',
            'working_directory': os.getcwd()
        }
        
        response = {
            'status': 'ok',
            'message': 'Server status',
            'uptime_seconds': uptime,
            'components': components,
            'system': system_info,
            'timestamp': time.time()
        }
        
        service_logger.debug(f"返回status响应: {response}")
        return jsonify(response)
    except Exception as e:
        service_logger.error(f"处理status请求时出错: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': 'Internal server error'}), 500


if __name__ == '__main__':
    """启动服务器"""
    try:
        # 配置服务器参数
        host = '127.0.0.1'
        port = 5000
        debug = True
        
        service_logger.info(f"启动服务器，监听地址: {host}:{port}, 调试模式: {debug}")
        
        # 使用Flask内置服务器（开发模式）
        app.run(host=host, port=port, debug=debug, threaded=True)
        
    except KeyboardInterrupt:
        service_logger.info("服务器已被用户中断")
    except Exception as e:
        service_logger.error(f"服务器启动失败: {str(e)}")
        import traceback
        service_logger.error(traceback.format_exc())
        print(f"错误: 服务器启动失败 - {str(e)}")
        sys.exit(1)