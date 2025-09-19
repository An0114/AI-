# AI智能体爬虫程序

一个集成了CLIP等大模型的智能爬虫系统，包含客户端与服务端架构，并提供图形用户界面。

## 功能特点

- **智能网页爬取**：支持多深度网页爬取，可配置爬取规则
- **AI辅助分析**：集成CLIP等大模型，支持图像-文本分析、零样本分类等功能
- **图形用户界面**：基于PyQt5开发的友好界面，支持可视化操作
- **服务端架构**：基于Flask的RESTful API服务，支持远程调用
- **并行爬取**：支持多线程并行爬取，提高效率
- **结果导出**：支持将爬取结果导出为JSON、CSV等格式

## 项目结构

```
├── main.py                # 主程序入口
├── requirements.txt       # 项目依赖
├── server/                # 服务端代码
│   └── server.py          # Flask服务端实现
├── client/                # 客户端代码
│   └── gui.py             # PyQt5图形界面实现
├── agent/                 # AI模型相关代码
│   └── ai_model.py        # 大模型封装（CLIP等）
├── crawler/               # 爬虫相关代码
│   └── web_crawler.py     # 网页爬虫实现
└── utils/                 # 工具类
    ├── logger.py          # 日志工具
    └── file_utils.py      # 文件处理工具
```

## 安装指南

### 1. 克隆项目

```bash
# 克隆项目到本地
```

### 2. 安装依赖

```bash
# 使用pip安装所有依赖
pip install -r requirements.txt

# 注意：CLIP库可能需要特殊安装
# 如果上面的安装失败，可以尝试单独安装CLIP
pip install git+https://github.com/openai/CLIP.git
```

### 3. 安装Chrome浏览器（用于Selenium）

如果需要使用Selenium进行动态网页爬取，请确保已安装Chrome浏览器。程序会自动下载匹配的ChromeDriver。

## 使用方法

### 1. 启动完整系统（服务端+客户端）

```bash
python main.py --all
```

### 2. 仅启动服务端

```bash
python main.py --server
```

### 3. 仅启动客户端

```bash
python main.py --client
```

## 界面说明

客户端GUI包含四个主要选项卡：

1. **网页爬取**：设置爬取参数并执行爬取任务
   - 目标URL：输入要爬取的网站地址
   - 爬取深度：设置爬取的链接层级深度
   - 启用AI分析：选择是否使用AI模型进行内容分析
   - 关键词筛选：设置关键词进行内容过滤

2. **AI分析**：使用AI模型分析文本或图像内容
   - AI模型：选择使用的AI模型（如CLIP）
   - 分析任务：选择分析类型（分类、相似度等）
   - 分析内容：输入要分析的文本内容

3. **爬取结果**：查看和管理爬取结果
   - 左侧列表显示所有爬取任务
   - 右侧显示选中任务的详细结果

4. **设置**：配置系统参数
   - 服务器地址：设置服务端的访问地址
   - 其他设置选项

## 服务端API说明

服务端提供RESTful API接口，主要包括：

### 1. 心跳检测
```
GET /api/ping
```

### 2. 执行爬取任务
```
POST /api/crawl
参数：
{
  "url": "https://example.com",  # 目标URL
  "depth": 1,                    # 爬取深度
  "use_ai": false,               # 是否使用AI分析
  "ai_model": "clip",            # AI模型类型
  "keywords": []                 # 关键词列表
}
```

### 3. AI内容分析
```
POST /api/analyze
参数：
{
  "content": "要分析的内容",       # 分析内容
  "model_type": "clip",          # 模型类型
  "task": "classification"       # 分析任务
}
```

### 4. 列出可用模型
```
GET /api/models
```

## 配置说明

爬虫的主要配置参数包括：

- `max_depth`：最大爬取深度，默认为2
- `max_pages`：最大爬取页面数，默认为100
- `timeout`：请求超时时间，默认为10秒
- `delay`：爬取延迟，默认为1秒
- `use_selenium`：是否使用Selenium，默认为false
- `download_images`：是否下载图片，默认为false
- `image_dir`：图片保存目录，默认为'./images'

## 注意事项

1. 使用前请确保已安装所有依赖
2. 大规模爬取时请遵守网站的robots.txt规则
3. 使用AI模型时可能需要较大的内存空间
4. 首次使用CLIP模型时会自动下载模型权重，可能需要一定时间

## 开发说明

### 1. 扩展新的AI模型

可以在`agent/ai_model.py`中扩展新的模型支持：

1. 在`_init_xxx_model`方法中实现模型初始化
2. 在`_analyze_with_xxx`方法中实现分析逻辑
3. 在`analyze`方法中添加对新模型的支持

### 2. 扩展爬虫功能

可以在`crawler/web_crawler.py`中扩展爬虫功能：

1. 添加新的内容提取器
2. 实现新的链接过滤规则
3. 优化并行爬取策略

## License

MIT