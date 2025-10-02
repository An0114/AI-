#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试视频爬取和下载功能
"""
import os
import sys
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from crawler.web_crawler import WebCrawler

def test_douyin_video_crawling():
    """测试抖音视频爬取"""
    print("开始测试抖音视频爬取...")
    
    # 配置爬虫
    config = {
        'use_selenium': True,
        'chrome_headless': True,
        'download_videos': True,
        'video_dir': './test_videos',  # 使用测试目录
        'extract_videos': True,
        'max_depth': 1,  # 只爬取当前页面
        'max_pages': 1,
        'timeout': 30,  # 增加超时时间
    }
    
    # 确保测试目录存在
    os.makedirs(config['video_dir'], exist_ok=True)
    
    # 创建爬虫实例
    crawler = WebCrawler(config=config)
    
    # 测试URL（可以根据实际情况修改）
    # test_url = "https://www.douyin.com/video/7123456789012345678"  # 示例抖音视频URL
    test_url = "https://www.bilibili.com/video/BV1aG4y1t7fV"  # 示例B站视频URL
    
    # 执行爬取
        try:
            crawl_result = crawler.crawl(
                url=test_url,
                use_ai=False,  # 暂时不使用AI
                keywords=None,
                depth=0
            )
            
            # 打印爬取结果统计
            print(f"爬取完成，共爬取 {crawl_result['pages_crawled']} 个页面")
            print(f"成功: {crawl_result['success_pages']}, 失败: {crawl_result['failed_pages']}")
            
            # 检查是否有视频
            has_videos = False
            if crawl_result.get('results'):
                print(f"获取到 {len(crawl_result['results'])} 个页面的内容")
                
                for page_content in crawl_result['results']:
                    if page_content.get('videos') and len(page_content.get('videos', [])) > 0:
                        has_videos = True
                        print(f"在页面 {page_content.get('url')} 找到视频：{len(page_content['videos'])} 个")
                        for video in page_content['videos']:
                            print(f"视频标题: {video.get('title')}")
                            print(f"视频URL: {video.get('url')}")
                            print(f"视频本地路径: {video.get('local_path')}")
        
            if has_videos:
                print(f"\n视频已保存在: {os.path.abspath(config['video_dir'])}")
            else:
                print("没有找到视频")
                
            # 保存结果到文件
            with open('test_video_results.json', 'w', encoding='utf-8') as f:
                json.dump(crawl_result, f, ensure_ascii=False, indent=2)
            print("爬取结果已保存到 test_video_results.json")
            
        except Exception as e:
            print(f"爬取过程中发生错误: {str(e)}")
            # 尝试保存部分结果
            try:
                with open('test_video_results.json', 'w', encoding='utf-8') as f:
                    json.dump({'error': str(e)}, f, ensure_ascii=False, indent=2)
            except:
                pass
    
    finally:
        # 清理资源
        if crawler.driver:
            crawler.driver.quit()

if __name__ == "__main__":
    test_douyin_video_crawling()