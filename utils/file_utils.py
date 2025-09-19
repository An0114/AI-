#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
文件工具模块
提供文件读写、保存爬虫结果等功能
"""

import os
import sys
import json
import pickle
import csv
import shutil
import hashlib
import time
from datetime import datetime

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

# 设置日志
file_logger = setup_logger('file_utils', 'file_utils.log')


def ensure_dir(directory):
    """确保目录存在，如果不存在则创建
    
    Args:
        directory (str): 目录路径
    """
    if not os.path.exists(directory):
        try:
            os.makedirs(directory)
            file_logger.info(f"创建目录成功: {directory}")
        except Exception as e:
            file_logger.error(f"创建目录失败 {directory}: {str(e)}")
            raise


def save_to_file(content, file_path, mode='w', encoding='utf-8'):
    """将内容保存到文件
    
    Args:
        content: 要保存的内容，可以是字符串、字典等
        file_path (str): 文件路径
        mode (str): 文件打开模式
        encoding (str): 文件编码
    
    Returns:
        bool: 是否保存成功
    """
    # 确保目录存在
    dir_path = os.path.dirname(file_path)
    if dir_path:
        ensure_dir(dir_path)
    
    try:
        # 根据内容类型选择不同的保存方式
        if isinstance(content, dict) or isinstance(content, list):
            # 保存为JSON文件
            with open(file_path, 'w', encoding=encoding) as f:
                json.dump(content, f, ensure_ascii=False, indent=2)
        elif isinstance(content, bytes):
            # 保存二进制文件
            with open(file_path, 'wb') as f:
                f.write(content)
        else:
            # 保存为文本文件
            with open(file_path, mode, encoding=encoding) as f:
                f.write(str(content))
                
        file_logger.info(f"文件保存成功: {file_path}")
        return True
        
    except Exception as e:
        file_logger.error(f"文件保存失败 {file_path}: {str(e)}")
        return False


def load_from_file(file_path, encoding='utf-8'):
    """从文件加载内容
    
    Args:
        file_path (str): 文件路径
        encoding (str): 文件编码
        
    Returns:
        加载的内容，如果文件不存在或加载失败则返回None
    """
    if not os.path.exists(file_path):
        file_logger.warning(f"文件不存在: {file_path}")
        return None
    
    try:
        # 尝试作为JSON文件加载
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                return json.load(f)
        except json.JSONDecodeError:
            # 如果不是JSON文件，尝试作为普通文本文件加载
            with open(file_path, 'r', encoding=encoding) as f:
                return f.read()
                
    except Exception as e:
        file_logger.error(f"文件加载失败 {file_path}: {str(e)}")
        return None


def save_crawl_results(results, output_dir='./results', format='json', include_timestamp=True):
    """保存爬虫结果
    
    Args:
        results (dict): 爬虫结果
        output_dir (str): 输出目录
        format (str): 输出格式，支持 'json', 'csv', 'pickle'
        include_timestamp (bool): 文件名是否包含时间戳
        
    Returns:
        str: 保存的文件路径
    """
    # 确保输出目录存在
    ensure_dir(output_dir)
    
    # 生成文件名
    base_name = 'crawl_results'
    if include_timestamp:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"{base_name}_{timestamp}"
    
    # 根据格式保存结果
    if format.lower() == 'json':
        file_path = os.path.join(output_dir, f"{base_name}.json")
        save_to_file(results, file_path)
        
    elif format.lower() == 'csv':
        file_path = os.path.join(output_dir, f"{base_name}.csv")
        save_results_to_csv(results, file_path)
        
    elif format.lower() == 'pickle':
        file_path = os.path.join(output_dir, f"{base_name}.pkl")
        save_to_pickle(results, file_path)
        
    else:
        raise ValueError(f"不支持的输出格式: {format}")
        
    return file_path


def save_results_to_csv(results, file_path):
    """将爬虫结果保存为CSV文件
    
    Args:
        results (dict): 爬虫结果
        file_path (str): CSV文件路径
    """
    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            # 定义CSV字段
            fieldnames = ['url', 'title', 'text', 'images_count', 'links_count', 'timestamp']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            
            # 写入表头
            writer.writeheader()
            
            # 写入每行数据
            for page in results.get('results', []):
                # 跳过失败的页面
                if 'error' in page:
                    continue
                    
                # 准备行数据
                row = {
                    'url': page.get('url', ''),
                    'title': page.get('title', ''),
                    'text': page.get('text', '')[:500] + '...' if len(page.get('text', '')) > 500 else page.get('text', ''),  # 限制文本长度
                    'images_count': len(page.get('images', [])),
                    'links_count': len(page.get('links', [])),
                    'timestamp': page.get('timestamp', time.time())
                }
                writer.writerow(row)
                
        file_logger.info(f"CSV文件保存成功: {file_path}")
        
    except Exception as e:
        file_logger.error(f"CSV文件保存失败 {file_path}: {str(e)}")
        raise


def save_to_pickle(data, file_path):
    """将数据保存为pickle文件
    
    Args:
        data: 要保存的数据
        file_path (str): pickle文件路径
    """
    try:
        with open(file_path, 'wb') as f:
            pickle.dump(data, f)
            
        file_logger.info(f"Pickle文件保存成功: {file_path}")
        
    except Exception as e:
        file_logger.error(f"Pickle文件保存失败 {file_path}: {str(e)}")
        raise


def load_from_pickle(file_path):
    """从pickle文件加载数据
    
    Args:
        file_path (str): pickle文件路径
        
    Returns:
        加载的数据，如果文件不存在或加载失败则返回None
    """
    if not os.path.exists(file_path):
        file_logger.warning(f"文件不存在: {file_path}")
        return None
    
    try:
        with open(file_path, 'rb') as f:
            return pickle.load(f)
            
    except Exception as e:
        file_logger.error(f"Pickle文件加载失败 {file_path}: {str(e)}")
        return None


def clear_directory(directory):
    """清空目录中的所有文件和子目录
    
    Args:
        directory (str): 要清空的目录
    """
    if not os.path.exists(directory):
        file_logger.warning(f"目录不存在: {directory}")
        return
    
    try:
        for filename in os.listdir(directory):
            file_path = os.path.join(directory, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
                
        file_logger.info(f"目录清空成功: {directory}")
        
    except Exception as e:
        file_logger.error(f"目录清空失败 {directory}: {str(e)}")
        raise


def get_file_hash(file_path, algorithm='md5'):
    """计算文件的哈希值
    
    Args:
        file_path (str): 文件路径
        algorithm (str): 哈希算法，支持 'md5', 'sha1', 'sha256'
        
    Returns:
        str: 文件的哈希值
    """
    if not os.path.exists(file_path):
        file_logger.warning(f"文件不存在: {file_path}")
        return None
    
    try:
        # 创建哈希对象
        hash_obj = hashlib.new(algorithm)
        
        # 分块读取文件并更新哈希值
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
                
        return hash_obj.hexdigest()
        
    except Exception as e:
        file_logger.error(f"计算文件哈希值失败 {file_path}: {str(e)}")
        return None


def get_file_size(file_path):
    """获取文件大小
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        int: 文件大小（字节），如果文件不存在则返回-1
    """
    if not os.path.exists(file_path):
        file_logger.warning(f"文件不存在: {file_path}")
        return -1
    
    try:
        return os.path.getsize(file_path)
        
    except Exception as e:
        file_logger.error(f"获取文件大小失败 {file_path}: {str(e)}")
        return -1


def get_file_info(file_path):
    """获取文件信息
    
    Args:
        file_path (str): 文件路径
        
    Returns:
        dict: 文件信息字典
    """
    if not os.path.exists(file_path):
        file_logger.warning(f"文件不存在: {file_path}")
        return None
    
    try:
        stats = os.stat(file_path)
        return {
            'path': file_path,
            'size': stats.st_size,
            'created_time': stats.st_ctime,
            'modified_time': stats.st_mtime,
            'access_time': stats.st_atime,
            'is_file': os.path.isfile(file_path),
            'is_dir': os.path.isdir(file_path),
            'hash': get_file_hash(file_path)
        }
        
    except Exception as e:
        file_logger.error(f"获取文件信息失败 {file_path}: {str(e)}")
        return None


def list_files(directory, extension=None, recursive=False):
    """列出目录中的文件
    
    Args:
        directory (str): 目录路径
        extension (str): 文件扩展名过滤，例如 '.txt'
        recursive (bool): 是否递归列出子目录中的文件
        
    Returns:
        list: 文件路径列表
    """
    if not os.path.exists(directory):
        file_logger.warning(f"目录不存在: {directory}")
        return []
    
    result = []
    
    try:
        if recursive:
            for root, _, files in os.walk(directory):
                for file in files:
                    if extension and not file.endswith(extension):
                        continue
                    result.append(os.path.join(root, file))
        else:
            for file in os.listdir(directory):
                file_path = os.path.join(directory, file)
                if os.path.isfile(file_path):
                    if extension and not file.endswith(extension):
                        continue
                    result.append(file_path)
                    
    except Exception as e:
        file_logger.error(f"列出文件失败 {directory}: {str(e)}")
        return []
        
    return result


def copy_file(src, dst):
    """复制文件
    
    Args:
        src (str): 源文件路径
        dst (str): 目标文件路径
        
    Returns:
        bool: 是否复制成功
    """
    if not os.path.exists(src):
        file_logger.warning(f"源文件不存在: {src}")
        return False
    
    # 确保目标目录存在
    dst_dir = os.path.dirname(dst)
    if dst_dir:
        ensure_dir(dst_dir)
    
    try:
        shutil.copy2(src, dst)
        file_logger.info(f"文件复制成功: {src} -> {dst}")
        return True
        
    except Exception as e:
        file_logger.error(f"文件复制失败 {src} -> {dst}: {str(e)}")
        return False


def move_file(src, dst):
    """移动文件
    
    Args:
        src (str): 源文件路径
        dst (str): 目标文件路径
        
    Returns:
        bool: 是否移动成功
    """
    if not os.path.exists(src):
        file_logger.warning(f"源文件不存在: {src}")
        return False
    
    # 确保目标目录存在
    dst_dir = os.path.dirname(dst)
    if dst_dir:
        ensure_dir(dst_dir)
    
    try:
        shutil.move(src, dst)
        file_logger.info(f"文件移动成功: {src} -> {dst}")
        return True
        
    except Exception as e:
        file_logger.error(f"文件移动失败 {src} -> {dst}: {str(e)}")
        return False


# 示例用法
if __name__ == '__main__':
    # 测试文件保存和加载
    test_data = {
        'name': '测试数据',
        'value': 123,
        'items': [1, 2, 3]
    }
    
    # 保存为JSON文件
    json_path = './test_data.json'
    save_to_file(test_data, json_path)
    
    # 加载JSON文件
    loaded_data = load_from_file(json_path)
    print(f"加载的JSON数据: {loaded_data}")
    
    # 保存为pickle文件
    pickle_path = './test_data.pkl'
    save_to_pickle(test_data, pickle_path)
    
    # 加载pickle文件
    loaded_pickle = load_from_pickle(pickle_path)
    print(f"加载的pickle数据: {loaded_pickle}")
    
    # 测试文件信息获取
    file_info = get_file_info(json_path)
    print(f"文件信息: {file_info}")
    
    print("文件工具测试完成")