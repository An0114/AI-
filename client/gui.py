#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI智能体爬虫客户端GUI
提供用户友好的界面来控制爬虫和查看结果
"""

import sys
import os
import json
import requests
import time
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QLabel, QLineEdit, QPushButton, QTextEdit, QProgressBar, 
    QTabWidget, QGroupBox, QCheckBox, QComboBox, QFileDialog, 
    QMessageBox, QListWidget, QListWidgetItem, QSplitter, QTreeWidget, 
    QTreeWidgetItem, QHeaderView
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QUrl
from PyQt5.QtGui import QFont, QIcon, QColor, QTextCursor

# 确保中文显示正常
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
plt.rcParams["font.family"] = ["SimHei", "WenQuanYi Micro Hei", "Heiti TC"]

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

# 设置日志
client_logger = setup_logger('client', 'client.log')

class CrawlThread(QThread):
    """爬虫线程，用于在后台执行爬取任务"""
    update_signal = pyqtSignal(str)
    complete_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    progress_signal = pyqtSignal(int)
    
    def __init__(self, url, depth=1, use_ai=False, ai_model='clip', keywords=None):
        super().__init__()
        self.url = url
        self.depth = depth
        self.use_ai = use_ai
        self.ai_model = ai_model
        self.keywords = keywords or []
        self.server_url = "http://127.0.0.1:5000/api"
        self.running = True
        
    def run(self):
        try:
            self.update_signal.emit(f"开始爬取: {self.url}")
            
            # 准备请求数据
            data = {
                'url': self.url,
                'depth': self.depth,
                'use_ai': self.use_ai,
                'ai_model': self.ai_model,
                'keywords': self.keywords
            }
            
            # 发送请求到服务端
            self.update_signal.emit("正在连接服务器...")
            response = requests.post(f"{self.server_url}/crawl", json=data, timeout=300)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    self.update_signal.emit("爬取完成！")
                    self.complete_signal.emit(result.get('data'))
                else:
                    error_msg = result.get('message', '未知错误')
                    self.error_signal.emit(f"爬取失败: {error_msg}")
            else:
                self.error_signal.emit(f"服务器响应错误: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("无法连接到服务器，请确保服务端已启动")
        except requests.exceptions.Timeout:
            self.error_signal.emit("请求超时")
        except Exception as e:
            self.error_signal.emit(f"爬取过程中发生错误: {str(e)}")
        finally:
            self.progress_signal.emit(100)
    
    def stop(self):
        self.running = False
        self.quit()

class AIModelAnalyzer(QThread):
    """AI模型分析线程"""
    update_signal = pyqtSignal(str)
    complete_signal = pyqtSignal(dict)
    error_signal = pyqtSignal(str)
    
    def __init__(self, content, model_type='clip', task='classification'):
        super().__init__()
        self.content = content
        self.model_type = model_type
        self.task = task
        self.server_url = "http://127.0.0.1:5000/api"
    
    def run(self):
        try:
            self.update_signal.emit(f"开始AI分析，模型: {self.model_type}")
            
            # 准备请求数据
            data = {
                'content': self.content,
                'model_type': self.model_type,
                'task': self.task
            }
            
            # 发送请求到服务端
            response = requests.post(f"{self.server_url}/analyze", json=data, timeout=60)
            
            if response.status_code == 200:
                result = response.json()
                if result.get('status') == 'success':
                    self.update_signal.emit("AI分析完成！")
                    self.complete_signal.emit(result.get('data'))
                else:
                    error_msg = result.get('message', '未知错误')
                    self.error_signal.emit(f"AI分析失败: {error_msg}")
            else:
                self.error_signal.emit(f"服务器响应错误: {response.status_code}")
                
        except requests.exceptions.ConnectionError:
            self.error_signal.emit("无法连接到服务器，请确保服务端已启动")
        except Exception as e:
            self.error_signal.emit(f"AI分析过程中发生错误: {str(e)}")

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        self.crawl_thread = None
        self.ai_thread = None
        self.crawl_results = []
        self.init_ui()
        
    def init_ui(self):
        """初始化用户界面"""
        # 设置窗口标题和大小
        self.setWindowTitle("AI智能体爬虫")
        self.setGeometry(100, 100, 1200, 800)
        
        # 创建中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 创建主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡控件
        self.tabs = QTabWidget()
        
        # 创建爬虫选项卡
        self.crawl_tab = QWidget()
        self.init_crawl_tab()
        self.tabs.addTab(self.crawl_tab, "网页爬取")
        
        # 创建AI分析选项卡
        self.ai_tab = QWidget()
        self.init_ai_tab()
        self.tabs.addTab(self.ai_tab, "AI分析")
        
        # 创建结果查看选项卡
        self.results_tab = QWidget()
        self.init_results_tab()
        self.tabs.addTab(self.results_tab, "爬取结果")
        
        # 创建设置选项卡
        self.settings_tab = QWidget()
        self.init_settings_tab()
        self.tabs.addTab(self.settings_tab, "设置")
        
        # 添加选项卡到主布局
        main_layout.addWidget(self.tabs)
        
        # 创建状态栏
        self.statusBar().showMessage("就绪")
        
    def init_crawl_tab(self):
        """初始化爬虫选项卡"""
        layout = QVBoxLayout(self.crawl_tab)
        
        # 创建输入区域
        input_group = QGroupBox("爬取设置")
        input_layout = QVBoxLayout()
        
        # URL输入
        url_layout = QHBoxLayout()
        url_label = QLabel("目标URL:")
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://example.com")
        url_layout.addWidget(url_label)
        url_layout.addWidget(self.url_input)
        
        # 爬取深度设置
        depth_layout = QHBoxLayout()
        depth_label = QLabel("爬取深度:")
        self.depth_combo = QComboBox()
        self.depth_combo.addItems(["1", "2", "3", "5", "10"])
        depth_layout.addWidget(depth_label)
        depth_layout.addWidget(self.depth_combo)
        depth_layout.addStretch()
        
        # AI设置
        ai_layout = QHBoxLayout()
        self.use_ai_check = QCheckBox("启用AI分析")
        ai_model_label = QLabel("AI模型:")
        self.ai_model_combo = QComboBox()
        self.ai_model_combo.addItems(["clip"])
        self.ai_model_combo.setEnabled(False)
        self.use_ai_check.stateChanged.connect(
            lambda state: self.ai_model_combo.setEnabled(state == Qt.Checked)
        )
        ai_layout.addWidget(self.use_ai_check)
        ai_layout.addWidget(ai_model_label)
        ai_layout.addWidget(self.ai_model_combo)
        ai_layout.addStretch()
        
        # 关键词输入
        keywords_layout = QHBoxLayout()
        keywords_label = QLabel("关键词筛选:")
        self.keywords_input = QLineEdit()
        self.keywords_input.setPlaceholderText("用逗号分隔，如：Python,AI,爬虫")
        keywords_layout.addWidget(keywords_label)
        keywords_layout.addWidget(self.keywords_input)
        
        # 添加到输入布局
        input_layout.addLayout(url_layout)
        input_layout.addLayout(depth_layout)
        input_layout.addLayout(ai_layout)
        input_layout.addLayout(keywords_layout)
        input_group.setLayout(input_layout)
        
        # 创建控制按钮
        control_layout = QHBoxLayout()
        self.start_button = QPushButton("开始爬取")
        self.start_button.clicked.connect(self.start_crawling)
        self.stop_button = QPushButton("停止爬取")
        self.stop_button.clicked.connect(self.stop_crawling)
        self.stop_button.setEnabled(False)
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addStretch()
        
        # 创建进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        
        # 创建日志显示区域
        log_group = QGroupBox("爬取日志")
        log_layout = QVBoxLayout()
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        log_group.setLayout(log_layout)
        
        # 添加到主布局
        layout.addWidget(input_group)
        layout.addLayout(control_layout)
        layout.addWidget(self.progress_bar)
        layout.addWidget(log_group)
        
    def init_ai_tab(self):
        """初始化AI分析选项卡"""
        layout = QVBoxLayout(self.ai_tab)
        
        # 创建输入区域
        input_group = QGroupBox("AI分析设置")
        input_layout = QVBoxLayout()
        
        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("AI模型:")
        self.ai_analyze_model_combo = QComboBox()
        self.ai_analyze_model_combo.addItems(["clip"])
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.ai_analyze_model_combo)
        model_layout.addStretch()
        
        # 任务类型
        task_layout = QHBoxLayout()
        task_label = QLabel("分析任务:")
        self.ai_task_combo = QComboBox()
        self.ai_task_combo.addItems(["classification", "similarity", "captioning"])
        task_layout.addWidget(task_label)
        task_layout.addWidget(self.ai_task_combo)
        task_layout.addStretch()
        
        # 添加到输入布局
        input_layout.addLayout(model_layout)
        input_layout.addLayout(task_layout)
        input_group.setLayout(input_layout)
        
        # 创建内容输入区域
        content_group = QGroupBox("分析内容")
        content_layout = QVBoxLayout()
        self.ai_content_text = QTextEdit()
        self.ai_content_text.setPlaceholderText("输入要分析的文本内容...")
        content_layout.addWidget(self.ai_content_text)
        content_group.setLayout(content_layout)
        
        # 创建控制按钮
        control_layout = QHBoxLayout()
        self.analyze_button = QPushButton("开始分析")
        self.analyze_button.clicked.connect(self.start_analysis)
        control_layout.addWidget(self.analyze_button)
        control_layout.addStretch()
        
        # 创建结果显示区域
        result_group = QGroupBox("AI分析结果")
        result_layout = QVBoxLayout()
        self.ai_result_text = QTextEdit()
        self.ai_result_text.setReadOnly(True)
        result_layout.addWidget(self.ai_result_text)
        result_group.setLayout(result_layout)
        
        # 添加到主布局
        layout.addWidget(input_group)
        layout.addWidget(content_group)
        layout.addLayout(control_layout)
        layout.addWidget(result_group)
        
    def init_results_tab(self):
        """初始化结果查看选项卡"""
        layout = QVBoxLayout(self.results_tab)
        
        # 创建分割器
        splitter = QSplitter(Qt.Vertical)
        
        # 创建结果列表
        results_group = QGroupBox("爬取结果列表")
        results_layout = QVBoxLayout()
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.show_result_details)
        results_layout.addWidget(self.results_list)
        results_group.setLayout(results_layout)
        
        # 创建结果详情显示区域
        details_group = QGroupBox("结果详情")
        details_layout = QVBoxLayout()
        self.result_details_text = QTextEdit()
        self.result_details_text.setReadOnly(True)
        details_layout.addWidget(self.result_details_text)
        details_group.setLayout(details_layout)
        
        # 添加到分割器
        splitter.addWidget(results_group)
        splitter.addWidget(details_group)
        
        # 设置分割器比例
        splitter.setSizes([300, 500])
        
        # 添加到主布局
        layout.addWidget(splitter)
        
    def init_settings_tab(self):
        """初始化设置选项卡"""
        layout = QVBoxLayout(self.settings_tab)
        
        # 创建服务器设置
        server_group = QGroupBox("服务器设置")
        server_layout = QVBoxLayout()
        
        # 服务器地址
        server_url_layout = QHBoxLayout()
        server_url_label = QLabel("服务器地址:")
        self.server_url_input = QLineEdit("http://127.0.0.1:5000")
        server_url_layout.addWidget(server_url_label)
        server_url_layout.addWidget(self.server_url_input)
        
        # 添加到服务器布局
        server_layout.addLayout(server_url_layout)
        server_group.setLayout(server_layout)
        
        # 创建其他设置
        other_group = QGroupBox("其他设置")
        other_layout = QVBoxLayout()
        
        # 保存设置按钮
        save_layout = QHBoxLayout()
        self.save_settings_button = QPushButton("保存设置")
        self.save_settings_button.clicked.connect(self.save_settings)
        save_layout.addWidget(self.save_settings_button)
        save_layout.addStretch()
        
        # 添加到其他布局
        other_layout.addLayout(save_layout)
        other_group.setLayout(other_layout)
        
        # 添加到主布局
        layout.addWidget(server_group)
        layout.addWidget(other_group)
        layout.addStretch()
        
    def start_crawling(self):
        """开始爬取任务"""
        url = self.url_input.text().strip()
        if not url:
            QMessageBox.warning(self, "警告", "请输入目标URL")
            return
        
        # 检查URL格式
        if not url.startswith(('http://', 'https://')):
            url = 'http://' + url
            self.url_input.setText(url)
        
        # 获取其他参数
        depth = int(self.depth_combo.currentText())
        use_ai = self.use_ai_check.isChecked()
        ai_model = self.ai_model_combo.currentText()
        
        # 解析关键词
        keywords_text = self.keywords_input.text().strip()
        keywords = [kw.strip() for kw in keywords_text.split(',')] if keywords_text else []
        
        # 禁用开始按钮，启用停止按钮
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        
        # 清空日志和进度条
        self.log_text.clear()
        self.progress_bar.setValue(0)
        
        # 创建并启动爬虫线程
        self.crawl_thread = CrawlThread(url, depth, use_ai, ai_model, keywords)
        self.crawl_thread.update_signal.connect(self.append_log)
        self.crawl_thread.complete_signal.connect(self.on_crawl_complete)
        self.crawl_thread.error_signal.connect(self.on_crawl_error)
        self.crawl_thread.progress_signal.connect(self.update_progress)
        self.crawl_thread.start()
        
        # 更新状态栏
        self.statusBar().showMessage(f"正在爬取: {url}")
        
    def stop_crawling(self):
        """停止爬取任务"""
        if self.crawl_thread and self.crawl_thread.isRunning():
            self.crawl_thread.stop()
            self.append_log("爬取任务已停止")
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.statusBar().showMessage("就绪")
            
    def append_log(self, message):
        """向日志区域添加消息"""
        self.log_text.append(f"[{time.strftime('%H:%M:%S')}] {message}")
        # 滚动到底部
        self.log_text.moveCursor(QTextCursor.End)
        
    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)
        
    def on_crawl_complete(self, data):
        """爬取完成后的处理"""
        self.append_log("爬取任务已完成")
        
        # 保存结果
        self.crawl_results.append(data)
        
        # 更新结果列表
        url = data.get('url', '未知URL')
        title = data.get('title', '未获取标题')
        item = QListWidgetItem(f"{title} - {url}")
        item.setData(Qt.UserRole, len(self.crawl_results) - 1)  # 存储索引
        self.results_list.addItem(item)
        
        # 恢复按钮状态
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # 更新状态栏
        self.statusBar().showMessage("就绪")
        
    def on_crawl_error(self, error_msg):
        """爬取错误时的处理"""
        self.append_log(f"错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
        
        # 恢复按钮状态
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        
        # 更新状态栏
        self.statusBar().showMessage("就绪")
        
    def show_result_details(self, item):
        """显示结果详情"""
        index = item.data(Qt.UserRole)
        if 0 <= index < len(self.crawl_results):
            result = self.crawl_results[index]
            # 格式化结果为JSON字符串
            formatted_result = json.dumps(result, ensure_ascii=False, indent=2)
            self.result_details_text.setText(formatted_result)
            
    def start_analysis(self):
        """开始AI分析"""
        content = self.ai_content_text.toPlainText().strip()
        if not content:
            QMessageBox.warning(self, "警告", "请输入要分析的内容")
            return
        
        # 获取参数
        model_type = self.ai_analyze_model_combo.currentText()
        task = self.ai_task_combo.currentText()
        
        # 禁用分析按钮
        self.analyze_button.setEnabled(False)
        
        # 清空结果区域
        self.ai_result_text.clear()
        self.ai_result_text.append("正在进行AI分析，请稍候...")
        
        # 创建并启动AI分析线程
        self.ai_thread = AIModelAnalyzer(content, model_type, task)
        self.ai_thread.update_signal.connect(self.ai_result_text.append)
        self.ai_thread.complete_signal.connect(self.on_ai_complete)
        self.ai_thread.error_signal.connect(self.on_ai_error)
        self.ai_thread.start()
        
    def on_ai_complete(self, data):
        """AI分析完成后的处理"""
        # 格式化结果为JSON字符串
        formatted_result = json.dumps(data, ensure_ascii=False, indent=2)
        self.ai_result_text.append("\n分析结果:\n")
        self.ai_result_text.append(formatted_result)
        
        # 恢复按钮状态
        self.analyze_button.setEnabled(True)
        
    def on_ai_error(self, error_msg):
        """AI分析错误时的处理"""
        self.ai_result_text.append(f"\n错误: {error_msg}")
        QMessageBox.critical(self, "错误", error_msg)
        
        # 恢复按钮状态
        self.analyze_button.setEnabled(True)
        
    def save_settings(self):
        """保存设置"""
        # 这里可以实现保存设置的逻辑
        QMessageBox.information(self, "提示", "设置已保存")
        
    def closeEvent(self, event):
        """关闭窗口时的处理"""
        # 停止所有线程
        if self.crawl_thread and self.crawl_thread.isRunning():
            self.crawl_thread.stop()
            self.crawl_thread.wait()
        
        if self.ai_thread and self.ai_thread.isRunning():
            self.ai_thread.quit()
            self.ai_thread.wait()
        
        event.accept()


def run_gui():
    """运行客户端GUI"""
    app = QApplication(sys.argv)
    
    # 设置应用程序样式
    app.setStyle("Fusion")
    
    # 创建主窗口
    window = MainWindow()
    window.show()
    
    # 捕获异常并记录日志
    try:
        sys.exit(app.exec_())
    except Exception as e:
        client_logger.error(f"客户端崩溃: {str(e)}")
        raise


if __name__ == '__main__':
    run_gui()