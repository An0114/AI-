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
            'use_selenium': True,  # 设为True以支持抖音等需要JavaScript渲染的页面
            'chrome_headless': True,
            'allow_domains': [],  # 允许的域名列表，为空表示不限制
            'deny_domains': [],   # 禁止的域名列表
            'download_images': False,
            'image_dir': './images',
            'download_videos': True,   # 默认启用视频下载
            'video_dir': './videos',   # 视频保存目录
            'follow_links': True,
            'extract_text': True,
            'extract_images': True,
            'extract_videos': True,    # 新增：提取视频
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
            
        # 创建视频保存目录
        if self.config['download_videos']:
            os.makedirs(self.config['video_dir'], exist_ok=True)
            
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
    
    def close(self):
        """关闭爬虫资源（兼容接口）"""
        # 调用已有的close_selenium方法来关闭资源
        self.close_selenium()
    
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
                
                # 针对不同网站设置不同的等待时间
                wait_time = 2  # 默认等待时间
                if 'iqiyi.com' in url:
                    # 爱奇艺页面需要更长时间加载视频资源
                    wait_time = 12  # 增加等待时间到12秒
                    # 特别针对爱奇艺的等待策略
                    print("正在加载爱奇艺页面，等待JavaScript渲染...")
                    # 等待视频播放器元素加载
                    time.sleep(4)
                    # 尝试执行一些JavaScript来触发视频加载
                    try:
                        # 滚动到视频区域
                        self.driver.execute_script("window.scrollTo(0, 500);")
                        time.sleep(2)
                        # 执行更多的JavaScript来模拟真实用户行为
                        self.driver.execute_script("document.documentElement.scrollTop = 300;")
                        time.sleep(1)
                        self.driver.execute_script("document.documentElement.scrollTop = 600;")
                        time.sleep(1)
                        # 尝试点击视频区域以触发加载
                        video_elements = self.driver.find_elements_by_css_selector('video, .player-container, .iqp-player, #flashbox')
                        if video_elements:
                            try:
                                self.driver.execute_script("arguments[0].click();", video_elements[0])
                                print("尝试点击视频区域...")
                            except:
                                pass
                        # 执行更多JavaScript来触发视频数据加载
                        self.driver.execute_script("console.log('Triggering video load...');")
                        time.sleep(1)
                        # 再等待一会儿
                        time.sleep(4)
                    except Exception as e:
                        print(f"执行JavaScript时出错: {str(e)}")
                elif 'douyin.com' in url or 'tiktok.com' in url:
                    wait_time = 4  # 抖音页面也需要较长时间
                
                time.sleep(wait_time)  # 等待页面加载
                
                # 尝试滚动页面以触发视频加载
                if 'iqiyi.com' in url:
                    self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    time.sleep(2)  # 等待滚动后的内容加载
                    # 再滚动回视频区域
                    self.driver.execute_script("window.scrollTo(0, 500);")
                    time.sleep(3)  # 增加等待时间
                
                content = self.driver.page_source
                print(f"成功获取页面内容，长度: {len(content)} 字符")
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
        """从HTML内容中提取视频信息
        
        Args:
            url (str): 页面URL
            html_content (str): HTML内容
            
        Returns:
            list: 视频列表
        """
        videos = []
        try:
            # 1. 首先通过video标签提取视频
            soup = BeautifulSoup(html_content, 'html.parser')
            video_tags = soup.find_all('video')
            
            for video in video_tags:
                video_url = None
                # 尝试从src属性获取视频URL
                if video.get('src'):
                    video_url = video.get('src')
                # 尝试从data-src属性获取视频URL
                elif video.get('data-src'):
                    video_url = video.get('data-src')
                # 尝试从source标签获取视频URL
                elif video.find('source'):
                    source = video.find('source')
                    video_url = source.get('src') if source.get('src') else None
                
                if video_url:
                    # 标准化URL
                    if video_url.startswith('//'):
                        video_url = 'https:' + video_url
                    elif not video_url.startswith('http'):
                        # 构建绝对URL
                        video_url = urljoin(url, video_url)
                    
                    if video_url not in [v['url'] for v in videos]:
                        print(f"通过video标签找到视频: {video_url}")
                        video_path = None
                        if self.config['download_videos']:
                            video_path = self.download_video(video_url)
                        
                        videos.append({
                            'url': video_url,
                            'type': video.get('type') or 'video/mp4',
                            'title': video.get('title') or '视频',
                            'path': video_path
                        })
            
            # 2. 从script标签中提取视频URL
            script_tags = soup.find_all('script')
            
            for script in script_tags:
                script_text = script.string
                if script_text:
                    # 尝试匹配.mp4文件URL
                    mp4_pattern = r'https?://[^"\']*\.mp4[^"\']*'
                    mp4_matches = re.findall(mp4_pattern, script_text)
                    
                    for match in mp4_matches:
                        # 过滤掉错误提示视频
                        if 'app-error-tip' not in match and match not in [v['url'] for v in videos]:
                            print(f"从script标签找到MP4视频: {match}")
                            video_path = None
                            if self.config['download_videos']:
                                video_path = self.download_video(match)
                            
                            videos.append({
                                'url': match,
                                'type': 'video/mp4',
                                'title': '视频',
                                'path': video_path
                            })
                    
                    # 尝试匹配其他可能的视频URL格式
                    video_patterns = [
                        r'video_url\s*[:=]\s*["\']([^"\']+)',
                        r'video_path\s*[:=]\s*["\']([^"\']+)',
                        r'videoLink\s*[:=]\s*["\']([^"\']+)',
                        # 爱奇艺特定模式 - 增强版本
                        r'videoId\s*[:=]\s*["\']([^"]+)',
                        r'playerId\s*[:=]\s*["\']([^"]+)',
                        r'"url"\s*:\s*["\']([^"\']+\.mp4[^"\']*)',
                        r'"url"\s*:\s*["\']([^"]+\.mp4[^"]*)',
                        r'"m3u8"\s*:\s*["\']([^"]+)',
                        r'"mainUrl"\s*:\s*["\']([^"]+)',
                        r'"backupUrl"\s*:\s*["\']([^"]+)',
                        r'"videoUrl"\s*:\s*["\']([^"\']+)',
                        # 额外的爱奇艺特定模式
                        r'qiyiPlayerConfig\s*=\s*(\{.*?\});',
                        r'Q\.Player\s*\(\s*\{.*?tvid\s*:\s*["\']?([^"\'\s,]+)',
                        r'tvid\s*:\s*["\']?([^"\'\s,]+)',
                        r'vid\s*:\s*["\']?([^"\'\s,]+)',
                        r'id\s*=\s*["\']player_([^"\']+)',
                        r'src\s*=\s*["\']([^"\']+\.mp4)["\']',
                        r'data-src\s*=\s*["\']([^"\']+\.mp4)["\']',
                        # 新增的爱奇艺模式
                        r'"playInfo"\s*:\s*(\{[^\}]+\})',
                        r'"adaptiveVideos"\s*:\s*\[([^\]]+)\]',
                        r'"clarity"\s*:\s*\{([^\}]+)\}',
                        r'"programVideo"\s*:\s*(\{[^\}]+\})',
                        r'"vrsVideo"\s*:\s*(\{[^\}]+\})',
                    ]
                    
                    for pattern in video_patterns:
                        matches = re.findall(pattern, script_text)
                        for match in matches:
                            # 确保是有效的URL
                            if isinstance(match, tuple):
                                match = match[0]  # 取第一个捕获组
                            
                            if match.startswith('//'):
                                match = 'https:' + match
                            elif not match.startswith('http'):
                                # 对于爱奇艺的特殊ID，我们可以尝试构建API URL
                                if 'iqiyi.com' in url and len(match) > 5 and '.' not in match:
                                    # 尝试使用已知的爱奇艺视频API构建URL
                                    api_url = f"https://cache.video.iqiyi.com/dash?vid={match}&ran=0.12345&qyid=0123456789&v=0"
                                    match = api_url
                                else:
                                    continue
                            
                            if match not in [v['url'] for v in videos]:
                                video_path = None
                                if self.config['download_videos']:
                                    video_path = self.download_video(match)
                                
                                videos.append({
                                    'url': match,
                                    'type': 'video/mp4',
                                    'title': '视频',
                                    'path': video_path
                                })
            
            # 3. 特别针对爱奇艺页面的额外处理
            if 'iqiyi.com' in url:
                # 提取视频ID并尝试直接构建API请求
                video_ids = set()  # 使用集合去重
                
                # 尝试从script标签中提取多种可能的视频ID
                id_patterns = [
                    r'videoId\s*[:=]\s*["\']([^"]+)',
                    r'tvid\s*[:=]\s*["\']([^"]+)',
                    r'vid\s*[:=]\s*["\']([^"]+)',
                    r'vId\s*[:=]\s*["\']([^"]+)',
                    r'Q\.Player\s*\(\s*\{.*?tvid\s*:\s*["\']?([^"\'\s,]+)',
                    r'qiyiPlayerConfig\.tvid\s*=\s*["\']([^"]+)',
                    r'qiyiPlayerConfig\.vid\s*=\s*["\']([^"]+)',
                    # 新增的ID提取模式
                    r'"tvid"\s*:\s*["\']([^"\']+)',
                    r'"vid"\s*:\s*["\']([^"\']+)',
                    r'\btvid=([^&]+)',
                    r'\bvid=([^&]+)',
                    r'_tvid=([^&]+)',
                    r'_vid=([^&]+)',
                ]
                
                for pattern in id_patterns:
                    found_ids = re.findall(pattern, html_content)
                    for vid in found_ids:
                        if vid and vid.strip():
                            video_ids.add(vid.strip())
                
                # 尝试从URL中提取视频ID
                url_id_patterns = [
                    r'v_(\w+)\.html',
                    r'tvid=(\w+)',
                    r'vid=(\w+)',
                    r'/videos/(\w+)',
                    r'/v_(\w+)/',
                    r'play/(\w+)',
                ]
                
                for pattern in url_id_patterns:
                    url_match = re.search(pattern, url)
                    if url_match:
                        vid = url_match.group(1)
                        if vid and vid.strip():
                            video_ids.add(vid.strip())
                
                print(f"从页面提取到的视频ID: {video_ids}")
                
                # 使用提取的视频ID构建API请求
                for video_id in video_ids:
                    # 尝试不同的爱奇艺API端点
                    api_endpoints = [
                        f"https://cache.video.iqiyi.com/dash?vid={video_id}&ran=0.12345&qyid=0123456789&v=0",
                        f"https://player.video.iqiyi.com/apis/getSource?sources=3&tvid={video_id}",
                        f"https://mixer.video.iqiyi.com/jp/mixin/videos/{video_id}",
                        f"https://cors-anywhere.herokuapp.com/https://cache.video.iqiyi.com/dash?vid={video_id}&ran=0.12345&qyid=0123456789&v=0",  # 备用CORS代理
                        f"https://api.iqiyi.com/video/v1/video/videoInfo?aid=qc_100001_100102&tvid={video_id}",
                        f"https://pcw-api.iqiyi.com/albums/album/avlistinfo?aid={video_id}&page=1&size=50",
                        f"https://meta.video.iqiyi.com/videos/{video_id}",
                    ]
                    
                    # 增强的请求头，更像真实浏览器
                    enhanced_headers = {
                        'User-Agent': self.config['user_agent'],
                        'Referer': url,
                        'Origin': 'https://www.iqiyi.com',
                        'Accept': '*/*',
                        'Accept-Language': 'zh-CN,zh;q=0.9',
                        'Connection': 'keep-alive',
                        'X-Requested-With': 'XMLHttpRequest',
                        # 新增请求头
                        'Accept-Encoding': 'gzip, deflate, br',
                        'Cache-Control': 'no-cache',
                        'Pragma': 'no-cache',
                        'TE': 'Trailers',
                    }
                    
                    for endpoint in api_endpoints:
                        if endpoint not in [v['url'] for v in videos]:
                            try:
                                print(f"尝试访问爱奇艺API: {endpoint}")
                                # 尝试直接访问API获取视频源
                                # 使用更长的超时时间
                                
                                # 配置代理（可选）
                                proxies = None
                                # 如果需要使用代理，可以取消下面的注释
                                # proxies = {'http': 'http://127.0.0.1:7890', 'https': 'http://127.0.0.1:7890'}
                                
                                api_response = requests.get(
                                    endpoint,
                                    headers=enhanced_headers,
                                    timeout=15,  # 增加超时时间
                                    allow_redirects=True,
                                    proxies=proxies  # 使用代理
                                )
                                
                                # 检查响应状态
                                if api_response.status_code != 200:
                                    print(f"API请求失败，状态码: {api_response.status_code}")
                                    print(f"响应头: {api_response.headers}")
                                    print(f"响应内容前200字符: {api_response.text[:200]}...")
                                    continue
                                
                                # 尝试解析响应
                                try:
                                    api_data = api_response.json()
                                    print(f"成功解析API响应，包含{len(str(api_data))}个字符")
                                    print(f"响应结构: {list(api_data.keys())[:5]}...")  # 打印前5个键
                                    
                                    # 递归搜索字典中的URL
                                    def find_urls(data, url_list):
                                        if isinstance(data, dict):
                                            for key, value in data.items():
                                                # 检查各种可能包含视频URL的字段
                                                url_keys = ['url', 'm3u8', 'mainUrl', 'backupUrl', 'videoUrl', 'mp4', 'src']
                                                if key.lower() in url_keys and isinstance(value, str):
                                                    if any(ext in value.lower() for ext in ['.mp4', '.m3u8', '.ts', '.flv']):
                                                        url_list.append(value)
                                                # 检查嵌套结构
                                                elif isinstance(value, (dict, list)):
                                                    find_urls(value, url_list)
                                        elif isinstance(data, list):
                                            for item in data:
                                                find_urls(item, url_list)
                                    
                                    api_urls = []
                                    find_urls(api_data, api_urls)
                                    
                                    print(f"从API响应中提取到{len(api_urls)}个视频URL")
                                    
                                    for api_url in api_urls:
                                        # 过滤掉错误提示视频
                                        if 'app-error-tip' not in api_url and api_url not in [v['url'] for v in videos]:
                                            # 标准化URL
                                            if api_url.startswith('//'):
                                                api_url = 'https:' + api_url
                                            
                                            print(f"找到有效视频URL: {api_url}")
                                            video_path = None
                                            if self.config['download_videos']:
                                                video_path = self.download_video(api_url)
                                            
                                            videos.append({
                                                'url': api_url,
                                                'type': 'video/mp4' if '.mp4' in api_url else 'video/m3u8',
                                                'title': f'爱奇艺视频_{video_id}',
                                                'path': video_path
                                            })
                                except json.JSONDecodeError:
                                    # 如果不是JSON，尝试直接从响应文本中提取URL
                                    print("响应不是有效JSON，尝试直接提取URL")
                                    url_patterns = [
                                        r'https?://[^"\']*\.mp4[^"\']*',
                                        r'https?://[^"\']*\.m3u8[^"\']*',
                                        r'https?://[^"\']*\.ts[^"\']*'
                                    ]
                                    
                                    for pattern in url_patterns:
                                        matches = re.findall(pattern, api_response.text)
                                        for match in matches:
                                            if 'app-error-tip' not in match and match not in [v['url'] for v in videos]:
                                                print(f"从非JSON响应中提取到URL: {match}")
                                                video_path = None
                                                if self.config['download_videos']:
                                                    video_path = self.download_video(match)
                                                
                                                videos.append({
                                                    'url': match,
                                                    'type': 'video/mp4' if '.mp4' in match else 'video/m3u8',
                                                    'title': f'爱奇艺视频_{video_id}',
                                                    'path': video_path
                                                })
                            except Exception as e:
                                print(f"尝试访问爱奇艺API失败: {str(e)}")
                                # 即使API访问失败，也添加API端点作为可能的视频源
                                if endpoint not in [v['url'] for v in videos]:
                                    videos.append({
                                        'url': endpoint,
                                        'type': 'api_endpoint',
                                        'title': f'爱奇艺API端点_{video_id}',
                                        'path': None
                                    })
        except Exception as e:
            print(f"提取视频失败: {str(e)}")
            crawler_logger.error(f"提取视频失败 {url}: {str(e)}")
        
        return videos

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
            
    def download_video(self, video_url):
        """下载视频
        
        Args:
            video_url (str): 视频URL
            
        Returns:
            str: 保存的视频路径，或None（如果下载失败）
        """
        try:
            # 创建视频文件名（使用URL的哈希值）
            video_hash = hashlib.md5(video_url.encode()).hexdigest()
            # 获取文件扩展名
            parsed_url = urlparse(video_url)
            path = parsed_url.path
            ext = os.path.splitext(path)[1] if '.' in path else '.mp4'
            # 限制扩展名长度
            if len(ext) > 5:
                ext = '.mp4'
            
            # 特殊处理m3u8格式
            if '.m3u8' in video_url:
                ext = '.mp4'  # 最终保存为mp4格式
                print(f"检测到m3u8格式视频，将尝试下载并转换: {video_url}")
                
                # 简单的m3u8下载实现（需要更复杂的实现可以使用ffmpeg）
                try:
                    # 构建保存路径
                    video_filename = f"{video_hash}{ext}"
                    video_path = os.path.join(self.config['video_dir'], video_filename)
                    
                    # 如果文件已存在，直接返回路径
                    if os.path.exists(video_path):
                        return video_path
                    
                    # 下载m3u8文件
                    headers = {'User-Agent': self.config['user_agent']}
                    m3u8_response = requests.get(video_url, headers=headers, timeout=self.config['timeout'])
                    m3u8_response.raise_for_status()
                    
                    # 解析m3u8文件中的ts片段
                    ts_urls = []
                    for line in m3u8_response.text.split('\n'):
                        if line and not line.startswith('#'):
                            # 构建完整的ts文件URL
                            ts_url = line if line.startswith('http') else urljoin(video_url, line)
                            ts_urls.append(ts_url)
                    
                    print(f"找到{len(ts_urls)}个ts片段")
                    
                    # 如果找到了ts片段，尝试下载
                    if ts_urls:
                        with open(video_path, 'wb') as f:
                            for i, ts_url in enumerate(ts_urls):
                                try:
                                    print(f"下载ts片段 {i+1}/{len(ts_urls)}: {ts_url}")
                                    ts_response = requests.get(ts_url, headers=headers, timeout=self.config['timeout'], stream=True)
                                    ts_response.raise_for_status()
                                    for chunk in ts_response.iter_content(chunk_size=8192):
                                        if chunk:
                                            f.write(chunk)
                                except Exception as e:
                                    print(f"下载ts片段失败 {i+1}: {str(e)}")
                                    # 继续尝试下载其他片段
                                    continue
                        
                        print(f"m3u8视频下载完成: {video_path}")
                        return video_path
                    else:
                        print("未找到ts片段，使用普通下载方式")
                except Exception as e:
                    print(f"m3u8下载失败，尝试普通下载方式: {str(e)}")
                    # 继续使用普通下载方式
            
            # 普通视频下载
            # 构建保存路径
            video_filename = f"{video_hash}{ext}"
            video_path = os.path.join(self.config['video_dir'], video_filename)
            
            # 如果文件已存在，直接返回路径
            if os.path.exists(video_path):
                return video_path
            
            # 下载视频
            headers = {
                'User-Agent': self.config['user_agent'],
                'Referer': 'https://www.iqiyi.com/',  # 为爱奇艺视频设置特定的Referer
                'Accept': 'video/webm,video/ogg,video/*;q=0.9,application/ogg;q=0.7,audio/*;q=0.6,*/*;q=0.5',
                'Range': 'bytes=0-'  # 请求从文件开头下载
            }
            
            # 大文件下载，使用stream模式
            response = requests.get(video_url, headers=headers, timeout=self.config['timeout'], stream=True)
            response.raise_for_status()
            
            # 获取文件大小（如果可用）
            file_size = int(response.headers.get('content-length', 0))
            print(f"开始下载视频，URL: {video_url}, 预计大小: {file_size/1024/1024:.2f} MB")
            
            # 保存视频
            downloaded_size = 0
            with open(video_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)
                        # 打印下载进度
                        if file_size > 0:
                            progress = (downloaded_size / file_size) * 100
                            print(f"下载进度: {progress:.1f}% ({downloaded_size/1024/1024:.2f} MB/{file_size/1024/1024:.2f} MB)", end='\r')
            
            print(f"\n视频下载完成: {video_path}, 实际大小: {downloaded_size/1024/1024:.2f} MB")
            return video_path
            
        except Exception as e:
            print(f"下载视频失败 {video_url}: {str(e)}")
            crawler_logger.error(f"下载视频失败 {video_url}: {str(e)}")
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
                    
                    # 如果启用了AI功能，进行AI分析和内容总结
                    if use_ai and ai_model:
                        # 进行AI过滤
                        page_content = self.filter_with_ai(page_content, ai_model, keywords)
                        
                        # 自动进行内容总结
                        try:
                            # 获取页面文本内容
                            content_text = page_content.get('text', '')
                            if content_text:
                                # 调用AI模型进行文本总结
                                summary_result = ai_model.summarize_text(
                                    text=content_text,
                                    max_length=300,
                                    url=current_url  # 传递URL以便AI模型识别抖音等特殊内容
                                )
                                # 将总结结果添加到页面内容中
                                page_content['summary'] = summary_result
                        except Exception as e:
                            crawler_logger.error(f"内容总结失败: {str(e)}")
                            page_content['summary'] = {'status': 'error', 'error': str(e)}
                        
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