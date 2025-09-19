#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
日志工具模块
提供统一的日志记录功能
"""

import os
import sys
import logging
import time
from logging.handlers import RotatingFileHandler


def setup_logger(logger_name, log_file, level=logging.INFO):
    """设置日志记录器
    
    Args:
        logger_name (str): 日志记录器名称
        log_file (str): 日志文件路径
        level (int): 日志级别
        
    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 创建日志目录（如果不存在）
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 创建日志记录器
    logger = logging.getLogger(logger_name)
    logger.setLevel(level)
    
    # 避免重复添加处理器
    if not logger.handlers:
        # 创建格式化器
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # 创建文件处理器（支持日志轮转）
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        
        # 创建控制台处理器
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到记录器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
    
    return logger


def get_timestamp():
    """获取当前时间戳
    
    Returns:
        str: 格式化的时间戳字符串
    """
    return time.strftime('%Y%m%d_%H%M%S')


def log_exception(logger, message, exc_info=True):
    """记录异常信息
    
    Args:
        logger (logging.Logger): 日志记录器
        message (str): 错误消息
        exc_info (bool): 是否包含异常堆栈信息
    """
    logger.error(message, exc_info=exc_info)


def log_info(logger, message):
    """记录信息日志
    
    Args:
        logger (logging.Logger): 日志记录器
        message (str): 信息消息
    """
    logger.info(message)


def log_warning(logger, message):
    """记录警告日志
    
    Args:
        logger (logging.Logger): 日志记录器
        message (str): 警告消息
    """
    logger.warning(message)


def log_debug(logger, message):
    """记录调试日志
    
    Args:
        logger (logging.Logger): 日志记录器
        message (str): 调试消息
    """
    logger.debug(message)


# 示例用法
if __name__ == '__main__':
    # 创建日志记录器
    test_logger = setup_logger('test_logger', 'test.log')
    
    # 记录不同级别的日志
    log_debug(test_logger, "这是一条调试日志")
    log_info(test_logger, "这是一条信息日志")
    log_warning(test_logger, "这是一条警告日志")
    
    # 记录异常
    try:
        1/0
    except Exception:
        log_exception(test_logger, "发生了异常")
        
    print("日志记录完成，请查看 test.log 文件")