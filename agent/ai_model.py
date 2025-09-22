#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
AI模型封装模块
集成OpenCLIP等大模型，提供统一的接口进行内容分析
"""

import os
import sys
import logging
import torch
import numpy as np
from PIL import Image
import requests
from io import BytesIO
from transformers import pipeline
import time

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

# 设置日志
model_logger = setup_logger('ai_model', 'model.log')

class MockCLIPModel:
    """当真实模型无法加载时使用的模拟CLIP模型"""
    def __init__(self):
        self.name = "Mock CLIP Model"
        model_logger.warning("使用模拟CLIP模型，所有结果为示例数据")
        
    def encode_image(self, image):
        # 生成随机特征向量作为模拟
        return torch.randn(1, 512)
        
    def encode_text(self, text):
        # 生成随机特征向量作为模拟
        if isinstance(text, torch.Tensor) and text.dim() == 2:
            # 处理tokenized文本
            return torch.randn(text.shape[0], 512)
        return torch.randn(1, 512)

class MockProcessor:
    """模拟预处理处理器"""
    def __call__(self, image):
        # 简单的模拟预处理
        return torch.randn(3, 224, 224)

class AIModel:
    """AI模型封装类，提供统一的接口访问不同的AI模型"""
    def __init__(self, model_type='clip'):
        """初始化AI模型
        
        Args:
            model_type (str): 模型类型，支持 'clip', 'transformer' 等
        """
        self.model_type = model_type
        self.model = None
        self.preprocess = None
        self.tokenizer = None
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        self.is_mock = False  # 标记是否使用模拟模型
        self.has_real_model = False  # 标记是否加载了真实模型
        
        # 初始化模型
        self.initialize_model()
    
    def initialize_model(self):
        """初始化指定类型的模型"""
        try:
            if self.model_type == 'clip':
                self._init_clip_model()
            elif self.model_type == 'transformer':
                self._init_transformer_model()
            else:
                raise ValueError(f"不支持的模型类型: {self.model_type}")
            
            if self.is_mock:
                model_logger.warning(f"{self.model_type} 模拟模型已初始化")
            else:
                model_logger.info(f"{self.model_type} 真实模型初始化成功")
                self.has_real_model = True
            
        except Exception as e:
            model_logger.error(f"{self.model_type} 模型初始化失败: {str(e)}")
            # 记录详细的错误信息，方便调试
            import traceback
            model_logger.error(traceback.format_exc())
            
            # 尝试使用模拟模型作为最后的备选
            self._init_mock_model()
    
    def _init_clip_model(self):
        """初始化OpenCLIP模型"""
        try:
            # 尝试使用本地缓存的模型（如果存在）
            cache_dir = os.path.expanduser("~/.cache/open_clip")
            if os.path.exists(cache_dir) and len(os.listdir(cache_dir)) > 0:
                model_logger.info(f"尝试从本地缓存 {cache_dir} 加载模型")
            
            # 尝试方案1：直接使用OpenCLIP库
            import open_clip
            # 设置更长的超时时间
            import socket
            original_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)  # 设置30秒超时
            
            try:
                self.model, _, self.preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
                self.model = self.model.to(self.device)
                self.tokenizer = open_clip.get_tokenizer('ViT-B-32')
                model_logger.info("成功使用OpenCLIP库加载模型")
            finally:
                # 恢复原始超时设置
                socket.setdefaulttimeout(original_timeout)
                
        except (ImportError, RuntimeError, requests.exceptions.RequestException, socket.timeout) as e:
            model_logger.warning(f"OpenCLIP库加载失败: {str(e)}")
            
            try:
                # 方案2：尝试通过transformers库加载CLIP模型
                model_logger.info("尝试使用transformers库加载CLIP模型")
                from transformers import CLIPProcessor, CLIPModel
                
                # 尝试使用本地文件（如果指定了）
                clip_model_path = os.environ.get('CLIP_MODEL_PATH')
                if clip_model_path and os.path.exists(clip_model_path):
                    model_logger.info(f"从本地路径加载模型: {clip_model_path}")
                    self.model = CLIPModel.from_pretrained(clip_model_path).to(self.device)
                    self.preprocess = CLIPProcessor.from_pretrained(clip_model_path)
                else:
                    # 尝试从Hugging Face加载，但设置更长的超时
                    original_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(30)
                    try:
                        self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32", local_files_only=False).to(self.device)
                        self.preprocess = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32", local_files_only=False)
                        model_logger.info("成功使用transformers库加载CLIP模型")
                    except Exception as transformers_error:
                        model_logger.warning(f"transformers库加载CLIP模型失败: {str(transformers_error)}")
                        # 两个方案都失败，使用模拟模型
                        self._init_mock_model()
                    finally:
                        socket.setdefaulttimeout(original_timeout)
                
            except Exception as transformers_error:
                model_logger.error(f"transformers库加载异常: {str(transformers_error)}")
                # 两个方案都失败，使用模拟模型
                self._init_mock_model()
    
    def _init_transformer_model(self):
        """初始化Transformers模型"""
        try:
            # 尝试初始化transformers模型
            self.model = pipeline("text-classification", model="bert-base-chinese")
            model_logger.info("成功初始化Transformers模型")
        except Exception as e:
            model_logger.error(f"Transformers模型初始化失败: {str(e)}")
            # 使用模拟模型作为备选
            self._init_mock_model()
            
    def _init_mock_model(self):
        """初始化模拟模型作为备选方案"""
        model_logger.warning("无法加载真实模型，正在初始化模拟模型")
        self.is_mock = True
        
        if self.model_type == 'clip':
            self.model = MockCLIPModel()
            self.preprocess = MockProcessor()
            self.tokenizer = lambda texts: torch.randint(0, 10000, (len(texts), 77)) if isinstance(texts, list) else torch.randint(0, 10000, (1, 77))
            
            # 输出提示信息，告诉用户如何手动下载模型
            model_logger.info("\n===== 模型加载建议 =====")
            model_logger.info("1. 检查网络连接，确保能访问 huggingface.co")
            model_logger.info("2. 如果网络受限，可以手动下载模型权重并设置环境变量 CLIP_MODEL_PATH")
            model_logger.info("3. 模拟模型仅用于演示，不提供真实的AI分析能力")
            model_logger.info("========================\n")
    
    def analyze(self, content, task='classification'):
        """使用AI模型分析内容
        
        Args:
            content: 要分析的内容，可以是文本、图像路径或URL
            task (str): 分析任务，支持 'classification', 'similarity', 'captioning', 'summarization' 等
            
        Returns:
            dict: 分析结果
        """
        try:
            if task == 'summarization' and isinstance(content, str):
                # 文本总结任务
                return self.summarize_text(content)
                
            if self.is_mock:
                # 如果使用模拟模型，在结果中添加标记
                result = self._mock_analysis(content, task)
                result['_is_mock_result'] = True
                result['_model_type'] = self.model_type
                return result
                
            if self.model_type == 'clip':
                return self._analyze_with_clip(content, task)
            elif self.model_type == 'transformer':
                return self._analyze_with_transformer(content, task)
            else:
                return {'error': f"不支持的模型类型: {self.model_type}"}
                
        except Exception as e:
            model_logger.error(f"分析失败: {str(e)}")
            # 在分析出错时也返回模拟结果，避免完全失败
            mock_result = self._mock_analysis(content, task)
            mock_result['_is_mock_result'] = True
            mock_result['_error_message'] = str(e)
            return mock_result
    
    def _mock_analysis(self, content, task):
        """模拟模型的分析功能"""
        model_logger.info(f"使用模拟模型进行{task}任务分析")
        
        # 生成一些合理的模拟结果
        if task == 'classification':
            if self.model_type == 'clip' and isinstance(content, dict) and 'text' in content and 'image' in content:
                # 模拟CLIP零样本分类结果
                labels = content['text'] if isinstance(content['text'], list) else [content['text']]
                if not labels:
                    labels = ['类别1', '类别2', '类别3']
                
                results = []
                import random
                random.seed(int(time.time()))  # 使用时间戳作为随机种子，使结果可复现
                scores = [random.random() for _ in range(len(labels))]
                
                # 归一化分数
                total = sum(scores)
                probs = [score/total for score in scores] if total > 0 else [1.0/len(scores)]*len(scores)
                
                for i, (label, prob) in enumerate(zip(labels, probs)):
                    results.append({
                        'prompt': label,
                        'score': float(prob),
                        'rank': i + 1
                    })
                
                # 按分数排序
                results.sort(key=lambda x: x['score'], reverse=True)
                
                return {
                    'task': 'zero_shot_classification',
                    'image': content['image'],
                    'prompts': labels,
                    'results': results,
                    'top_prediction': results[0]['prompt'] if results else None,
                    'note': "此结果由模拟模型生成，仅供演示使用"
                }
                
            elif self.model_type == 'transformer' and isinstance(content, str):
                # 模拟文本分类结果
                return {
                    'task': 'text_classification',
                    'input': content,
                    'results': [{
                        'label': '积极',
                        'score': 0.75
                    }, {
                        'label': '消极',
                        'score': 0.25
                    }],
                    'note': "此结果由模拟模型生成，仅供演示使用"
                }
        
        elif task == 'similarity' and self.model_type == 'clip' and isinstance(content, dict) and 'text' in content and 'image' in content:
            # 模拟相似度计算结果
            import random
            random.seed(hash(content['text'] + str(content['image'])))  # 使用内容生成随机种子
            similarity = random.uniform(-0.5, 0.5)
            
            return {
                'task': 'text_image_similarity',
                'text': content['text'],
                'image': content['image'],
                'similarity_score': similarity,
                'interpretation': self._interpret_similarity_score(similarity),
                'note': "此结果由模拟模型生成，仅供演示使用"
            }
        
        elif task == 'captioning' and self.model_type == 'clip' and isinstance(content, str):
            # 模拟图像描述结果
            captions = [
                "这是一张示例图片",
                "图片中包含一些视觉元素",
                "这是一个模拟生成的描述",
                "此结果由模拟模型创建"
            ]
            
            return {
                'task': 'image_captioning',
                'image': content,
                'captions': captions,
                'note': "此结果由模拟模型生成，仅供演示使用"
            }
        
        elif task == 'summarization' and isinstance(content, str):
            # 模拟文本总结结果
            return self._mock_text_summary(content, 100)
        
        # 默认返回
        return {
            'status': 'success',
            'message': f"使用模拟{self.model_type}模型完成{task}任务",
            'note': "此结果由模拟模型生成，仅供演示使用"
        }
            
    def _mock_analysis(self, content, task):
        """模拟模型的分析功能"""
        model_logger.info(f"使用模拟模型进行{task}任务分析")
        
        # 生成一些合理的模拟结果
        if task == 'classification':
            if self.model_type == 'clip' and isinstance(content, dict) and 'text' in content and 'image' in content:
                # 模拟CLIP零样本分类结果
                labels = content['text'] if isinstance(content['text'], list) else [content['text']]
                if not labels:
                    labels = ['类别1', '类别2', '类别3']
                
                results = []
                import random
                random.seed(int(time.time()))  # 使用时间戳作为随机种子，使结果可复现
                scores = [random.random() for _ in range(len(labels))]
                
                # 归一化分数
                total = sum(scores)
                probs = [score/total for score in scores] if total > 0 else [1.0/len(scores)]*len(scores)
                
                for i, (label, prob) in enumerate(zip(labels, probs)):
                    results.append({
                        'prompt': label,
                        'score': float(prob),
                        'rank': i + 1
                    })
                
                # 按分数排序
                results.sort(key=lambda x: x['score'], reverse=True)
                
                return {
                    'task': 'zero_shot_classification',
                    'image': content['image'],
                    'prompts': labels,
                    'results': results,
                    'top_prediction': results[0]['prompt'] if results else None,
                    'note': "此结果由模拟模型生成，仅供演示使用"
                }
                
            elif self.model_type == 'transformer' and isinstance(content, str):
                # 模拟文本分类结果
                return {
                    'task': 'text_classification',
                    'input': content,
                    'results': [{
                        'label': '积极',
                        'score': 0.75
                    }, {
                        'label': '消极',
                        'score': 0.25
                    }],
                    'note': "此结果由模拟模型生成，仅供演示使用"
                }
        
        elif task == 'similarity' and self.model_type == 'clip' and isinstance(content, dict) and 'text' in content and 'image' in content:
            # 模拟相似度计算结果
            import random
            random.seed(hash(content['text'] + str(content['image'])))  # 使用内容生成随机种子
            similarity = random.uniform(-0.5, 0.5)
            
            return {
                'task': 'text_image_similarity',
                'text': content['text'],
                'image': content['image'],
                'similarity_score': similarity,
                'interpretation': self._interpret_similarity_score(similarity),
                'note': "此结果由模拟模型生成，仅供演示使用"
            }
        
        elif task == 'captioning' and self.model_type == 'clip' and isinstance(content, str):
            # 模拟图像描述结果
            captions = [
                "这是一张示例图片",
                "图片中包含一些视觉元素",
                "这是一个模拟生成的描述",
                "此结果由模拟模型创建"
            ]
            
            return {
                'task': 'image_captioning',
                'image': content,
                'captions': captions,
                'note': "此结果由模拟模型生成，仅供演示使用"
            }
        
        # 默认返回
        return {
            'status': 'success',
            'message': f"使用模拟{self.model_type}模型完成{task}任务",
            'note': "此结果由模拟模型生成，仅供演示使用"
        }
    
    def _analyze_with_clip(self, content, task):
        """使用CLIP模型进行分析"""
        if task == 'classification':
            # CLIP的零样本分类
            if isinstance(content, dict) and 'text' in content and 'image' in content:
                return self._clip_zero_shot_classification(content['text'], content['image'])
            else:
                return {'error': "CLIP零样本分类需要提供文本和图像"}
                
        elif task == 'similarity':
            # 计算文本和图像的相似度
            if isinstance(content, dict) and 'text' in content and 'image' in content:
                return self._clip_text_image_similarity(content['text'], content['image'])
            else:
                return {'error': "CLIP相似度计算需要提供文本和图像"}
                
        elif task == 'captioning':
            # 图像描述生成（使用预定义的描述模板）
            if isinstance(content, str) and (content.startswith(('http://', 'https://')) or os.path.exists(content)):
                return self._clip_image_captioning(content)
            else:
                return {'error': "CLIP图像描述需要提供有效的图像URL或路径"}
                
        else:
            return {'error': f"不支持的任务类型: {task}"}
    
    def _analyze_with_transformer(self, content, task):
        """使用Transformers模型进行分析"""
        if task == 'classification' and isinstance(content, str):
            # 文本分类
            result = self.model(content)
            return {
                'task': 'text_classification',
                'input': content,
                'results': result
            }
        else:
            return {'error': "Transformers模型目前仅支持文本分类任务"}
    
    def summarize_text(self, text, max_length=100):
        """文本总结功能
        
        Args:
            text (str): 要总结的文本
            max_length (int): 总结的最大长度
            
        Returns:
            dict: 总结结果
        """
        try:
            model_logger.info(f"执行文本总结，文本长度: {len(text)}, 最大总结长度: {max_length}")
            
            # 如果使用模拟模型，返回模拟结果
            if self.is_mock:
                return self._mock_text_summary(text, max_length)
                
            # 真实模型的总结功能（如果有）
            if self.model_type == 'transformer':
                # 尝试使用transformer模型进行总结
                # 注意：这里是简化实现，实际应用中应该使用专门的摘要模型
                model_logger.warning("当前模型不支持真实的文本总结，返回模拟结果")
                return self._mock_text_summary(text, max_length)
            else:
                model_logger.warning(f"{self.model_type}模型不支持文本总结，返回模拟结果")
                return self._mock_text_summary(text, max_length)
        except Exception as e:
            model_logger.error(f"文本总结失败: {str(e)}")
            # 出错时返回模拟结果
            return self._mock_text_summary(text, max_length)
    
    def _mock_text_summary(self, text, max_length):
        """模拟文本总结"""
        model_logger.info("使用模拟方法进行文本总结")
        
        # 简单的文本总结模拟：提取前几个句子
        sentences = text.split('.')
        summary_sentences = []
        current_length = 0
        
        for sentence in sentences:
            if not sentence.strip():
                continue
            
            sentence += '.'
            if current_length + len(sentence) <= max_length:
                summary_sentences.append(sentence)
                current_length += len(sentence)
            else:
                break
        
        summary = ''.join(summary_sentences)
        
        # 如果提取的句子不够，就截取文本
        if not summary or len(summary) < 10:
            summary = text[:max_length] + '...' if len(text) > max_length else text
        
        return {
            'status': 'success',
            'original_length': len(text),
            'summary_length': len(summary),
            'summary': summary,
            'is_mock': True,
            'note': "此结果由模拟方法生成，真实应用中建议使用专门的文本摘要模型"
        }
    
    def _clip_zero_shot_classification(self, text_prompts, image_path):
        """使用OpenCLIP进行零样本分类"""
        try:
            # 加载图像
            image = self._load_image(image_path)
            
            # 预处理图像
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # 使用tokenizer处理文本
            if hasattr(self, 'tokenizer') and self.tokenizer is not None:
                # OpenCLIP的tokenizer
                text_input = self.tokenizer(text_prompts).to(self.device)
            elif hasattr(self.preprocess, 'tokenizer'):
                # transformers的tokenizer
                text_input = self.preprocess.tokenizer(text_prompts, return_tensors="pt", padding=True).to(self.device)
            else:
                # 尝试直接使用预处理（旧版CLIP）
                text_input = [self.preprocess(text) for text in text_prompts]
                text_input = torch.cat(text_input).to(self.device)
            
            # 计算特征
            with torch.no_grad():
                if hasattr(self.model, 'encode_image') and hasattr(self.model, 'encode_text'):
                    # OpenCLIP或原生CLIP的API
                    image_features = self.model.encode_image(image_input)
                    
                    if isinstance(text_input, dict) and 'input_ids' in text_input:
                        # transformers的格式
                        text_features = self.model.encode_text(text_input['input_ids'])
                    else:
                        # OpenCLIP或原生CLIP的格式
                        text_features = self.model.encode_text(text_input)
                else:
                    # transformers的CLIPModel API
                    if isinstance(text_input, dict):
                        inputs = {'pixel_values': image_input, **text_input}
                    else:
                        inputs = {'pixel_values': image_input, 'input_ids': text_input}
                    outputs = self.model(**inputs)
                    image_features = outputs.image_embeds
                    text_features = outputs.text_embeds
                
                # 归一化特征
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # 计算相似度
                similarity = (image_features @ text_features.T).squeeze(0).cpu().numpy()
                
                # 获取分类结果
                if len(similarity.shape) == 0:
                    similarity = np.array([similarity])
                probs = similarity.softmax(dim=0)
            
            # 整理结果
            results = []
            for i, (prompt, prob) in enumerate(zip(text_prompts, probs)):
                results.append({
                    'prompt': prompt,
                    'score': float(prob),
                    'rank': i + 1
                })
            
            # 按分数排序
            results.sort(key=lambda x: x['score'], reverse=True)
            
            return {
                'task': 'zero_shot_classification',
                'image': image_path,
                'prompts': text_prompts,
                'results': results,
                'top_prediction': results[0]['prompt'] if results else None
            }
            
        except Exception as e:
            model_logger.error(f"OpenCLIP零样本分类失败: {str(e)}")
            return {'error': str(e)}
    
    def _clip_text_image_similarity(self, text, image_path):
        """计算文本和图像的相似度"""
        try:
            # 加载图像
            image = self._load_image(image_path)
            
            # 预处理图像
            image_input = self.preprocess(image).unsqueeze(0).to(self.device)
            
            # 使用tokenizer处理文本
            if hasattr(self, 'tokenizer') and self.tokenizer is not None:
                # OpenCLIP的tokenizer
                text_input = self.tokenizer([text]).to(self.device)
            elif hasattr(self.preprocess, 'tokenizer'):
                # transformers的tokenizer
                text_input = self.preprocess.tokenizer([text], return_tensors="pt", padding=True).to(self.device)
            else:
                # 尝试直接使用预处理（旧版CLIP）
                text_input = self.preprocess(text).unsqueeze(0).to(self.device)
            
            # 计算特征
            with torch.no_grad():
                if hasattr(self.model, 'encode_image') and hasattr(self.model, 'encode_text'):
                    # OpenCLIP或原生CLIP的API
                    image_features = self.model.encode_image(image_input)
                    
                    if isinstance(text_input, dict) and 'input_ids' in text_input:
                        # transformers的格式
                        text_features = self.model.encode_text(text_input['input_ids'])
                    else:
                        # OpenCLIP或原生CLIP的格式
                        text_features = self.model.encode_text(text_input)
                else:
                    # transformers的CLIPModel API
                    if isinstance(text_input, dict):
                        inputs = {'pixel_values': image_input, **text_input}
                    else:
                        inputs = {'pixel_values': image_input, 'input_ids': text_input}
                    outputs = self.model(**inputs)
                    image_features = outputs.image_embeds
                    text_features = outputs.text_embeds
                
                # 归一化特征
                image_features = image_features / image_features.norm(dim=-1, keepdim=True)
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)
                
                # 计算相似度
                similarity = (image_features @ text_features.T).item()
            
            return {
                'task': 'text_image_similarity',
                'text': text,
                'image': image_path,
                'similarity_score': similarity,
                'interpretation': self._interpret_similarity_score(similarity)
            }
            
        except Exception as e:
            model_logger.error(f"OpenCLIP文本-图像相似度计算失败: {str(e)}")
            return {'error': str(e)}
    
    def _clip_image_captioning(self, image_path):
        """使用CLIP生成图像描述"""
        try:
            # 预定义的描述模板（简化版，实际应用中可以使用更复杂的模板）
            caption_templates = [
                "这是一张关于{category}的图片",
                "图片中有{object}",
                "这张图片展示了{scene}",
                "图片里有{number}个{object}",
                "这是一张{style}风格的图片"
            ]
            
            # 这里使用简化的方法，实际应用中可以结合其他模型如BLIP进行更准确的描述
            return {
                'task': 'image_captioning',
                'image': image_path,
                'captions': caption_templates,
                'note': "CLIP模型本身不直接支持图像描述生成，此功能使用预定义模板，建议使用专门的图像描述模型如BLIP"
            }
            
        except Exception as e:
            model_logger.error(f"CLIP图像描述生成失败: {str(e)}")
            return {'error': str(e)}
    
    def _load_image(self, image_path):
        """加载图像，支持本地路径和URL"""
        if image_path.startswith(('http://', 'https://')):
            # 从URL加载图像
            response = requests.get(image_path, timeout=10)
            response.raise_for_status()
            image = Image.open(BytesIO(response.content))
        else:
            # 从本地文件加载图像
            image = Image.open(image_path)
        
        # 转换为RGB
        if image.mode != 'RGB':
            image = image.convert('RGB')
            
        return image
    
    def _interpret_similarity_score(self, score):
        """解释相似度分数"""
        if score > 0.3:
            return "非常相似"
        elif score > 0.1:
            return "比较相似"
        elif score > -0.1:
            return "一般"
        elif score > -0.3:
            return "不太相似"
        else:
            return "非常不相似"
    
    def is_initialized(self):
        """检查模型是否初始化成功
        
        注意：即使返回True，也可能使用的是模拟模型
        使用has_real_model属性可以检查是否加载了真实模型
        """
        return self.model is not None
        
    def get_status(self):
        """获取模型当前状态信息"""
        return {
            'model_type': self.model_type,
            'has_real_model': self.has_real_model,
            'is_mock': self.is_mock,
            'device': str(self.device),
            'is_initialized': self.model is not None
        }


# 示例用法
if __name__ == '__main__':
    # 测试CLIP模型
    try:
        clip_model = AIModel(model_type='clip')
        if clip_model.is_initialized():
            print("CLIP模型初始化成功")
            # 这里可以添加更多的测试代码
        else:
            print("CLIP模型初始化失败")
            
    except Exception as e:
        print(f"测试失败: {str(e)}")