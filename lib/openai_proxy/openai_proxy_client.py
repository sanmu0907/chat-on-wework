#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAI Proxy API Client - OpenAI兼容格式
"""
import requests
from typing import Optional, Dict, List, Any


class OpenAIProxyClient:
    """OpenAI Proxy API客户端，兼容OpenAI格式"""

    def __init__(self, api_key: str, base_url: str = "https://api.example.com/v1"):
        """
        初始化客户端

        Args:
            api_key: API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')

    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    def list_models(self) -> requests.Response:
        """
        获取可用模型列表

        Returns:
            Response对象
        """
        url = f"{self.base_url}/models"
        response = requests.get(url, headers=self._get_headers(), timeout=10)
        return response

    def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float = 0.9,
        max_tokens: Optional[int] = None,
        top_p: float = 1.0,
        stream: bool = False,
        **kwargs
    ) -> requests.Response:
        """
        创建聊天补全

        Args:
            model: 模型名称
            messages: 消息列表，格式：[{"role": "user", "content": "hello"}]
            temperature: 温度参数（0-2）
            max_tokens: 最大token数
            top_p: top_p参数
            stream: 是否流式输出
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        url = f"{self.base_url}/chat/completions"

        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "top_p": top_p,
            "stream": stream
        }

        if max_tokens:
            payload["max_tokens"] = max_tokens

        # 添加其他参数
        payload.update(kwargs)

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            stream=stream,
            timeout=300  # 增加到5分钟，适应大模型响应时间
        )

        return response

    def image_generation(
        self,
        prompt: str,
        model: str = "dall-e-3",
        n: int = 1,
        size: str = "1024x1024",
        quality: str = "standard",
        **kwargs
    ) -> requests.Response:
        """
        生成图片

        Args:
            prompt: 图片描述
            model: 模型名称（如 dall-e-3, stable-diffusion, flux等）
            n: 生成数量
            size: 图片尺寸
            quality: 图片质量 (standard/hd)
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        url = f"{self.base_url}/images/generations"

        payload = {
            "model": model,
            "prompt": prompt,
            "n": n,
            "size": size,
            "quality": quality
        }

        # 添加其他参数
        payload.update(kwargs)

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            timeout=120  # 图片生成可能需要较长时间
        )

        return response

    def video_generation(
        self,
        prompt: str,
        model: str = "Grok-3",
        image_url: Optional[str] = None,
        duration: int = 5,
        aspect_ratio: str = "16:9",
        **kwargs
    ) -> requests.Response:
        """
        生成视频（支持文生视频和图生视频）

        Args:
            prompt: 视频描述
            model: 模型名称（如 Grok-3）
            image_url: 参考图片URL（图生视频时使用）
            duration: 视频时长（秒）
            aspect_ratio: 视频宽高比
            **kwargs: 其他参数

        Returns:
            Response对象
        """
        url = f"{self.base_url}/videos/generations"

        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
            "aspect_ratio": aspect_ratio
        }

        # 如果提供了图片URL，则为图生视频
        if image_url:
            payload["image_url"] = image_url

        # 添加其他参数
        payload.update(kwargs)

        response = requests.post(
            url,
            headers=self._get_headers(),
            json=payload,
            timeout=300  # 视频生成需要更长时间
        )

        return response
