#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
网页爬虫模块
实现智能网页爬取功能，支持基本爬取和AI辅助爬取
"""

import os
import sys
import time
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import hashlib
from concurrent.futures import ThreadPoolExecutor, as_completed
import re
import json
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger
from utils.file_utils import save_to_file

# 设置日志
crawler_logger = setup_logger('web_crawler', 'crawler.log')

class WebCrawler:
    """网页爬虫类，支持基本爬取和AI辅助爬取"""
    def __init__(self, config=None):
        """初始化爬虫
        
        Args:
            config (dict): 爬虫配置参数
        """
        # 合并默认配置和用户配置
        self.config = {
            'max_depth': 2,
            'max_pages': 100,
            'timeout': 10,
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'delay': 1,
            'use_selenium': False,
            'chrome_headless': True,
            'allow_domains': [],  # 允许的域名列表，为空表示不限制
            'deny_domains': [],   # 禁止的域名列表
            'download_images': False,
            'image_dir': './images',
            'follow_links': True,
            'extract_text': True,
            'extract_images': True,
            'extract_links': True,
            'extract_metadata': True,
        }
        
        if config:
            self.config.update(config)
            
        # 初始化爬虫状态
        self.visited_urls = set()
        self.url_queue = []
        self.results = []
        self.driver = None
        
        # 创建图片保存目录
        if self.config['download_images']:
            os.makedirs(self.config['image_dir'], exist_ok=True)
            
    def initialize_selenium(self):
        """初始化Selenium WebDriver"""
        if self.driver is None and self.config['use_selenium']:
            try:
                chrome_options = Options()
                if self.config['chrome_headless']:
                    chrome_options.add_argument('--headless')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument(f'user-agent={self.config["user_agent"]}')
                
                # 使用webdriver-manager自动下载和管理ChromeDriver
                self.driver = webdriver.Chrome(
                    service=Service(ChromeDriverManager().install()),
                    options=chrome_options
                )
                
                # 设置页面加载超时
                self.driver.set_page_load_timeout(self.config['timeout'])
                
                crawler_logger.info("Selenium WebDriver初始化成功")
                
            except Exception as e:
                crawler_logger.error(f"Selenium WebDriver初始化失败: {str(e)}")
                # 降级为使用requests
                self.config['use_selenium'] = False
    
    def close_selenium(self):
        """关闭Selenium WebDriver"""
        if self.driver is not None:
            try:
                self.driver.quit()
                self.driver = None
                crawler_logger.info("Selenium WebDriver已关闭")
            except Exception as e:
                crawler_logger.error(f"关闭Selenium WebDriver时出错: {str(e)}")
    
    def is_valid_url(self, url):
        """检查URL是否有效
        
        Args:
            url (str): 要检查的URL
            
        Returns:
            bool: URL是否有效
        """
        try:
            result = urlparse(url)
            # 检查是否有有效的scheme和netloc
            valid = all([result.scheme, result.netloc])
            
            # 检查域名限制
            if valid:
                domain = result.netloc
                # 如果有允许的域名列表，检查是否在列表中
                if self.config['allow_domains']:
                    valid = any(domain.endswith(allowed_domain) for allowed_domain in self.config['allow_domains'])
                # 检查是否在禁止的域名列表中
                if valid and self.config['deny_domains']:
                    valid = not any(domain.endswith(deny_domain) for deny_domain in self.config['deny_domains'])
            
            return valid
            
        except Exception:
            return False
    
    def normalize_url(self, url, base_url):
        """标准化URL
        
        Args:
            url (str): 要标准化的URL
            base_url (str): 基础URL，用于相对路径解析
            
        Returns:
            str: 标准化后的URL
        """
        # 解析基础URL
        base_parsed = urlparse(base_url)
        
        # 处理相对路径
        normalized_url = urljoin(base_url, url)
        
        # 解析标准化后的URL
        parsed = urlparse(normalized_url)
        
        # 移除URL中的锚点
        normalized_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        
        # 移除尾部的斜杠（除了根路径）
        if normalized_url.endswith('/') and len(normalized_url) > len(f"{parsed.scheme}://{parsed.netloc}") + 1:
            normalized_url = normalized_url[:-1]
            
        return normalized_url
    
    def fetch_page(self, url):
        """获取网页内容
        
        Args:
            url (str): 要获取的URL
            
        Returns:
            tuple: (status_code, content, error)
        """
        try:
            if self.config['use_selenium']:
                # 使用Selenium获取页面
                if self.driver is None:
                    self.initialize_selenium()
                    
                if self.driver is None:
                    # 如果Selenium初始化失败，降级使用requests
                    return self._fetch_with_requests(url)
                
                self.driver.get(url)
                time.sleep(2)  # 等待页面加载
                content = self.driver.page_source
                return 200, content, None
                
            else:
                # 使用requests获取页面
                return self._fetch_with_requests(url)
                
        except Exception as e:
            crawler_logger.error(f"获取页面失败 {url}: {str(e)}")
            return 500, None, str(e)
    
    def _fetch_with_requests(self, url):
        """使用requests库获取页面内容
        
        Args:
            url (str): 要获取的URL
            
        Returns:
            tuple: (status_code, content, error)
        """
        headers = {'User-Agent': self.config['user_agent']}
        try:
            response = requests.get(url, headers=headers, timeout=self.config['timeout'])
            response.raise_for_status()
            # 尝试获取页面编码并解码
            response.encoding = response.apparent_encoding
            return response.status_code, response.text, None
            
        except requests.exceptions.RequestException as e:
            error_msg = str(e)
            status_code = getattr(e.response, 'status_code', 500) if hasattr(e, 'response') else 500
            return status_code, None, error_msg
    
    def extract_content(self, url, html_content):
        """从HTML内容中提取信息
        
        Args:
            url (str): 页面URL
            html_content (str): HTML内容
            
        Returns:
            dict: 提取的内容
        """
        result = {
            'url': url,
            'title': '',
            'text': '',
            'images': [],
            'links': [],
            'metadata': {},
            'timestamp': time.time(),
        }
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 提取标题
            if self.config['extract_metadata']:
                title_tag = soup.find('title')
                result['title'] = title_tag.text.strip() if title_tag else 'No title'
                
                # 提取元数据
                meta_tags = soup.find_all('meta')
                metadata = {}
                for tag in meta_tags:
                    if tag.get('name'):
                        metadata[tag.get('name')] = tag.get('content', '')
                    elif tag.get('property'):
                        metadata[tag.get('property')] = tag.get('content', '')
                result['metadata'] = metadata
                
            # 提取文本
            if self.config['extract_text']:
                # 移除脚本和样式标签
                for script in soup(['script', 'style', 'noscript', 'iframe']):
                    script.extract()
                
                # 获取纯文本
                text = soup.get_text(separator='\n', strip=True)
                # 清理多余的空行
                text = '\n'.join([line.strip() for line in text.split('\n') if line.strip()])
                result['text'] = text
                
            # 提取图片
            if self.config['extract_images']:
                images = []
                img_tags = soup.find_all('img')
                for img in img_tags:
                    img_url = img.get('src')
                    if img_url:
                        # 标准化图片URL
                        img_url = self.normalize_url(img_url, url)
                        img_alt = img.get('alt', '')
                        img_title = img.get('title', '')
                        
                        # 下载图片（如果配置了）
                        img_path = None
                        if self.config['download_images']:
                            img_path = self.download_image(img_url)
                            
                        images.append({
                            'url': img_url,
                            'alt': img_alt,
                            'title': img_title,
                            'path': img_path
                        })
                result['images'] = images
                
            # 提取链接
            if self.config['extract_links']:
                links = []
                a_tags = soup.find_all('a', href=True)
                for a in a_tags:
                    link_url = a.get('href')
                    if link_url and not link_url.startswith('#'):
                        # 标准化链接URL
                        link_url = self.normalize_url(link_url, url)
                        link_text = a.get_text(strip=True)
                        link_title = a.get('title', '')
                        
                        # 检查链接是否有效
                        if self.is_valid_url(link_url):
                            links.append({
                                'url': link_url,
                                'text': link_text,
                                'title': link_title
                            })
                result['links'] = links
                
        except Exception as e:
            crawler_logger.error(f"提取内容失败 {url}: {str(e)}")
            result['error'] = str(e)
            
        return result
    
    def download_image(self, img_url):
        """下载图片
        
        Args:
            img_url (str): 图片URL
            
        Returns:
            str: 保存的图片路径，或None（如果下载失败）
        """
        try:
            # 创建图片文件名（使用URL的哈希值）
            img_hash = hashlib.md5(img_url.encode()).hexdigest()
            # 获取文件扩展名
            parsed_url = urlparse(img_url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1] if '.' in path else '.jpg'
            # 限制扩展名长度
            if len(ext) > 5:
                ext = '.jpg'
            
            # 构建保存路径
            img_filename = f"{img_hash}{ext}"
            img_path = os.path.join(self.config['image_dir'], img_filename)
            
            # 如果文件已存在，直接返回路径
            if os.path.exists(img_path):
                return img_path
                
            # 下载图片
            headers = {'User-Agent': self.config['user_agent']}
            response = requests.get(img_url, headers=headers, timeout=self.config['timeout'])
            response.raise_for_status()
            
            # 保存图片
            with open(img_path, 'wb') as f:
                f.write(response.content)
                
            return img_path
            
        except Exception as e:
            crawler_logger.error(f"下载图片失败 {img_url}: {str(e)}")
            return None
    
    def filter_with_ai(self, content, ai_model, keywords=None):
        """使用AI模型过滤内容
        
        Args:
            content (dict): 网页内容
            ai_model: AI模型实例
            keywords (list): 关键词列表
            
        Returns:
            dict: 包含过滤结果的内容
        """
        try:
            # 如果没有提供AI模型，直接返回内容
            if not ai_model:
                content['ai_analysis'] = {'status': 'skipped', 'reason': 'No AI model provided'}
                return content
                
            # 准备分析数据
            analysis_data = {
                'text': content.get('text', ''),
            }
            
            # 如果有图片，也进行分析
            if content.get('images'):
                # 选择第一张图片进行分析
                first_image = content['images'][0]
                if first_image.get('path') or first_image.get('url'):
                    analysis_data['image'] = first_image.get('path') or first_image.get('url')
                    
            # 如果提供了关键词，使用零样本分类
            if keywords:
                # 如果有关键词，使用零样本分类
                result = ai_model.analyze(analysis_data, task='classification')
                
            else:
                # 否则使用相似度分析（这里使用预设的通用类别）
                general_categories = [
                    "新闻文章", "技术博客", "产品页面", "博客文章",
                    "教程指南", "论坛讨论", "社交媒体", "电子商务"
                ]
                result = ai_model.analyze({**analysis_data, 'text': general_categories}, task='similarity')
                
            # 添加AI分析结果
            content['ai_analysis'] = {
                'status': 'completed',
                'results': result,
                'timestamp': time.time()
            }
            
            return content
            
        except Exception as e:
            crawler_logger.error(f"AI过滤失败: {str(e)}")
            content['ai_analysis'] = {'status': 'error', 'error': str(e)}
            return content
    
    def crawl(self, url, depth=1, use_ai=False, ai_model=None, keywords=None):
        """执行爬取任务
        
        Args:
            url (str): 起始URL
            depth (int): 爬取深度
            use_ai (bool): 是否使用AI过滤
            ai_model: AI模型实例
            keywords (list): 关键词列表
            
        Returns:
            dict: 爬取结果
        """
        # 重置爬虫状态
        self.visited_urls = set()
        self.url_queue = [(url, 0)]  # (url, current_depth)
        self.results = []
        
        # 初始化结果
        crawl_result = {
            'url': url,
            'depth': depth,
            'use_ai': use_ai,
            'start_time': time.time(),
            'pages_crawled': 0,
            'success_pages': 0,
            'failed_pages': 0,
            'results': [],
            'stats': {}
        }
        
        try:
            # 初始化Selenium（如果配置了）
            if self.config['use_selenium']:
                self.initialize_selenium()
                
            # 开始爬取
            while self.url_queue and len(self.visited_urls) < self.config['max_pages']:
                current_url, current_depth = self.url_queue.pop(0)
                
                # 检查URL是否已访问过或深度超过限制
                if current_url in self.visited_urls or current_depth > depth:
                    continue
                    
                # 记录已访问的URL
                self.visited_urls.add(current_url)
                
                # 记录爬取的页面数量
                crawl_result['pages_crawled'] += 1
                
                # 打印爬取信息
                crawler_logger.info(f"爬取: {current_url} (深度: {current_depth}/{depth})")
                
                # 获取页面内容
                status_code, html_content, error = self.fetch_page(current_url)
                
                if status_code == 200 and html_content:
                    # 提取页面内容
                    page_content = self.extract_content(current_url, html_content)
                    
                    # 如果启用了AI过滤，进行AI分析
                    if use_ai:
                        page_content = self.filter_with_ai(page_content, ai_model, keywords)
                        
                    # 添加到结果列表
                    self.results.append(page_content)
                    crawl_result['success_pages'] += 1
                    
                    # 如果启用了链接跟踪且当前深度小于最大深度，添加新的URL到队列
                    if self.config['follow_links'] and current_depth < depth:
                        for link in page_content.get('links', []):
                            link_url = link['url']
                            if link_url not in self.visited_urls and link_url not in [u for u, _ in self.url_queue]:
                                self.url_queue.append((link_url, current_depth + 1))
                                
                else:
                    # 记录失败的页面
                    failed_page = {
                        'url': current_url,
                        'status_code': status_code,
                        'error': error
                    }
                    self.results.append(failed_page)
                    crawl_result['failed_pages'] += 1
                    
                # 避免爬取过快，添加延迟
                time.sleep(self.config['delay'])
                
            # 整理最终结果
            crawl_result['results'] = self.results
            crawl_result['end_time'] = time.time()
            crawl_result['duration'] = crawl_result['end_time'] - crawl_result['start_time']
            crawl_result['stats'] = {
                'visited_urls': len(self.visited_urls),
                'success_rate': crawl_result['success_pages'] / crawl_result['pages_crawled'] if crawl_result['pages_crawled'] > 0 else 0,
                'avg_time_per_page': crawl_result['duration'] / crawl_result['pages_crawled'] if crawl_result['pages_crawled'] > 0 else 0
            }
            
            # 打印统计信息
            crawler_logger.info(f"爬取完成: {crawl_result['pages_crawled']} 页面，成功: {crawl_result['success_pages']}，失败: {crawl_result['failed_pages']}")
            crawler_logger.info(f"耗时: {crawl_result['duration']:.2f} 秒")
            
            return crawl_result
            
        except Exception as e:
            crawler_logger.error(f"爬取任务失败: {str(e)}")
            crawl_result['error'] = str(e)
            crawl_result['end_time'] = time.time()
            crawl_result['duration'] = crawl_result['end_time'] - crawl_result['start_time']
            return crawl_result
            
        finally:
            # 关闭Selenium（如果使用了）
            self.close_selenium()
            
    def crawl_parallel(self, url, depth=1, use_ai=False, ai_model=None, keywords=None, max_workers=4):
        """并行执行爬取任务
        
        Args:
            url (str): 起始URL
            depth (int): 爬取深度
            use_ai (bool): 是否使用AI过滤
            ai_model: AI模型实例
            keywords (list): 关键词列表
            max_workers (int): 最大工作线程数
            
        Returns:
            dict: 爬取结果
        """
        # 首先使用单线程爬取第一层，获取所有链接
        first_layer_result = self.crawl(url, depth=0, use_ai=use_ai, ai_model=ai_model, keywords=keywords)
        
        # 提取第一层页面中的链接作为第二层爬取的目标
        second_layer_urls = []
        for page in first_layer_result['results']:
            if 'links' in page:
                for link in page['links']:
                    if link['url'] not in self.visited_urls and len(second_layer_urls) < self.config['max_pages']:
                        second_layer_urls.append(link['url'])
                        
        # 如果没有达到最大深度，进行并行爬取
        if depth > 0:
            # 创建临时爬虫实例用于并行爬取
            temp_crawlers = []
            for _ in range(max_workers):
                temp_config = self.config.copy()
                temp_config['follow_links'] = False  # 并行爬取时不跟随链接
                temp_crawlers.append(WebCrawler(temp_config))
                
            # 记录并行爬取的结果
            parallel_results = []
            
            # 使用线程池执行并行爬取
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交任务
                future_to_url = {
                    executor.submit(crawler.crawl, url, depth=0, use_ai=use_ai, ai_model=ai_model, keywords=keywords): 
                    (crawler, url) 
                    for i, url in enumerate(second_layer_urls)
                    for crawler in [temp_crawlers[i % max_workers]]
                }
                
                # 处理完成的任务
                for future in as_completed(future_to_url):
                    crawler, url = future_to_url[future]
                    try:
                        result = future.result()
                        if result and result['results']:
                            parallel_results.extend(result['results'])
                            
                    except Exception as e:
                        crawler_logger.error(f"并行爬取失败 {url}: {str(e)}")
                        parallel_results.append({'url': url, 'error': str(e)})
            
            # 合并结果
            first_layer_result['results'].extend(parallel_results)
            first_layer_result['pages_crawled'] += len(parallel_results)
            first_layer_result['success_pages'] += sum(1 for page in parallel_results if 'error' not in page)
            first_layer_result['failed_pages'] += sum(1 for page in parallel_results if 'error' in page)
            
        return first_layer_result


# 示例用法
if __name__ == '__main__':
    # 创建爬虫实例
    crawler = WebCrawler({
        'max_pages': 10,
        'delay': 0.5,
        'use_selenium': False,
        'download_images': False
    })
    
    try:
        # 测试爬取
        result = crawler.crawl(
            url='https://www.example.com',
            depth=1,
            use_ai=False
        )
        
        # 打印结果摘要
        print(f"爬取完成，共爬取 {result['pages_crawled']} 页面")
        print(f"成功: {result['success_pages']}, 失败: {result['failed_pages']}")
        print(f"耗时: {result['duration']:.2f} 秒")
        
    except Exception as e:
        print(f"测试失败: {str(e)}")
    finally:
        # 确保Selenium被关闭
        crawler.close_selenium()