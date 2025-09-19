#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI智能体爬虫程序
包含客户端与服务端架构，使用CLIP等大模型实现智能爬虫功能
"""

import os
import sys
import argparse
from multiprocessing import Process
import time


def start_server():
    """启动服务端"""
    from server.server import run_server
    run_server()


def start_client():
    """启动客户端GUI"""
    from client.gui import run_gui
    run_gui()


def main():
    """主函数，解析命令行参数并启动相应组件"""
    parser = argparse.ArgumentParser(description='AI智能体爬虫程序')
    parser.add_argument('--server', action='store_true', help='仅启动服务端')
    parser.add_argument('--client', action='store_true', help='仅启动客户端')
    parser.add_argument('--all', action='store_true', help='同时启动服务端和客户端', default=True)
    
    args = parser.parse_args()
    
    processes = []
    
    if args.server or args.all:
        # 启动服务端进程
        server_process = Process(target=start_server)
        server_process.daemon = True
        server_process.start()
        processes.append(server_process)
        print("服务端已启动")
        
        # 等待服务端启动完成
        if args.all:
            time.sleep(2)
    
    if args.client or args.all:
        # 启动客户端
        try:
            start_client()
        except KeyboardInterrupt:
            print("客户端已关闭")
    
    # 等待所有进程结束
    for process in processes:
        if process.is_alive():
            process.join(1)


if __name__ == '__main__':
    main()