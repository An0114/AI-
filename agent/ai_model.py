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

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.logger import setup_logger

# 设置日志
model_logger = setup_logger('ai_model', 'model.log')

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
            
            model_logger.info(f"{self.model_type} 模型初始化成功")
            
        except Exception as e:
            model_logger.error(f"{self.model_type} 模型初始化失败: {str(e)}")
            # 记录详细的错误信息，方便调试
            import traceback
            model_logger.error(traceback.format_exc())
    
    def _init_clip_model(self):
        """初始化OpenCLIP模型"""
        try:
            import open_clip
            # 使用OpenCLIP加载模型
            self.model, _, self.preprocess = open_clip.create_model_and_transforms('ViT-B-32', pretrained='laion2b_s34b_b79k')
            self.model = self.model.to(self.device)
            self.tokenizer = open_clip.get_tokenizer('ViT-B-32')
        except ImportError:
            # 尝试通过transformers库加载CLIP模型作为备选方案
            model_logger.warning("直接导入OpenCLIP失败，尝试使用transformers库加载")
            from transformers import CLIPProcessor, CLIPModel
            self.model = CLIPModel.from_pretrained("openai/clip-vit-base-patch32").to(self.device)
            self.preprocess = CLIPProcessor.from_pretrained("openai/clip-vit-base-patch32")
    
    def _init_transformer_model(self):
        """初始化Transformers模型"""
        # 这里可以根据需要初始化其他transformers模型
        self.model = pipeline("text-classification", model="bert-base-chinese")
    
    def analyze(self, content, task='classification'):
        """使用AI模型分析内容
        
        Args:
            content: 要分析的内容，可以是文本、图像路径或URL
            task (str): 分析任务，支持 'classification', 'similarity', 'captioning' 等
            
        Returns:
            dict: 分析结果
        """
        try:
            if self.model_type == 'clip':
                return self._analyze_with_clip(content, task)
            elif self.model_type == 'transformer':
                return self._analyze_with_transformer(content, task)
            else:
                return {'error': f"不支持的模型类型: {self.model_type}"}
                
        except Exception as e:
            model_logger.error(f"分析失败: {str(e)}")
            return {'error': str(e)}
    
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
        """检查模型是否初始化成功"""
        return self.model is not None


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