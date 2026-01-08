#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
OpenAI Proxy Bot - 使用OpenAI兼容API的聊天机器人
"""
import json
import base64
import os
from bot.bot import Bot
from bot.chatgpt.chat_gpt_session import ChatGPTSession
from bot.session_manager import SessionManager
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from common import memory
from config import conf, load_config
from lib.openai_proxy.openai_proxy_client import OpenAIProxyClient


class OpenAIProxyBot(Bot):
    """OpenAI Proxy API聊天机器人"""

    def __init__(self):
        super().__init__()

        # 从配置中读取API配置（使用通用 OpenAI 兼容格式）
        self.api_key = conf().get("open_ai_api_key", "")
        self.api_base = conf().get("open_ai_api_base", "https://api.openai.com/v1")
        self.model = conf().get("model", "gpt-4o")

        # 初始化客户端
        self.client = OpenAIProxyClient(api_key=self.api_key, base_url=self.api_base)

        # 初始化会话管理器
        self.sessions = SessionManager(ChatGPTSession, model=self.model)

        # API参数配置
        self.args = {
            "model": self.model,
            "temperature": conf().get("temperature", 0.9),
            "top_p": conf().get("top_p", 1.0),
            "max_tokens": 2000,  # 固定值，可根据需要调整
        }

        logger.info(f"[OpenAIProxy] Bot initialized with model: {self.model}, api_base: {self.api_base}")

    def reply(self, query, context=None):
        """
        处理用户消息并返回回复

        Args:
            query: 用户查询内容
            context: 上下文信息

        Returns:
            Reply对象
        """
        # 处理图片识别
        if context.type == ContextType.IMAGE:
            if not conf().get("image_recognition", False):
                return Reply(ReplyType.ERROR, "图片识别功能未启用")

            logger.info(f"[OpenAIProxy] 收到图片消息: {query}")

            # 准备图片（下载到本地）
            cmsg = context.get("msg")
            if cmsg:
                cmsg.prepare()

            session_id = context["session_id"]

            # 检查是否有缓存的用户查询
            if session_id in memory.USER_IMAGE_CACHE:
                user_query = memory.USER_IMAGE_CACHE[session_id].get("query", "请描述这张图片")
                del memory.USER_IMAGE_CACHE[session_id]
            else:
                user_query = "请描述这张图片"

            # 读取图片并转换为base64
            try:
                with open(query, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')

                # 获取图片扩展名
                ext = os.path.splitext(query)[1].lower()
                mime_type = {
                    '.jpg': 'image/jpeg',
                    '.jpeg': 'image/jpeg',
                    '.png': 'image/png',
                    '.gif': 'image/gif',
                    '.webp': 'image/webp'
                }.get(ext, 'image/jpeg')

                # 构建vision消息
                messages = [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_query},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{mime_type};base64,{image_data}"
                            }
                        }
                    ]
                }]

                # 调用API（使用vision模型）
                vision_model = conf().get("vision_model") or self.model
                logger.info(f"[OpenAIProxy] 使用识图模型: {vision_model}")

                response = self.client.chat_completion(
                    model=vision_model,
                    messages=messages,
                    temperature=self.args["temperature"],
                    max_tokens=2000,
                    stream=False
                )

                if response.status_code != 200:
                    error_msg = f"图片识别失败，状态码: {response.status_code}"
                    try:
                        error_data = response.json()
                        error_msg += f", 错误: {error_data.get('error', {}).get('message', '未知错误')}"
                    except:
                        error_msg += f", 响应: {response.text}"

                    logger.error(f"[OpenAIProxy] {error_msg}")
                    return Reply(ReplyType.ERROR, error_msg)

                # 解析响应
                result = response.json()
                content = result["choices"][0]["message"]["content"]

                logger.info(f"[OpenAIProxy] 图片识别成功: {content[:100]}...")
                return Reply(ReplyType.TEXT, content)

            except FileNotFoundError:
                return Reply(ReplyType.ERROR, "图片文件不存在")
            except Exception as e:
                logger.error(f"[OpenAIProxy] 图片识别异常: {str(e)}")
                return Reply(ReplyType.ERROR, f"图片识别失败: {str(e)}")

        # 处理文本消息
        if context.type == ContextType.TEXT:
            logger.info(f"[OpenAIProxy] query={query}")

            session_id = context["session_id"]
            reply = None

            # 处理特殊命令
            clear_memory_commands = conf().get("clear_memory_commands", ["#清除记忆"])
            if query in clear_memory_commands:
                self.sessions.clear_session(session_id)
                reply = Reply(ReplyType.INFO, "记忆已清除")
            elif query == "#清除所有":
                self.sessions.clear_all_session()
                reply = Reply(ReplyType.INFO, "所有人记忆已清除")
            elif query == "#更新配置":
                load_config()
                reply = Reply(ReplyType.INFO, "配置已更新")

            if reply:
                return reply

            # 获取会话并添加用户消息
            session = self.sessions.session_query(query, session_id)
            logger.debug(f"[OpenAIProxy] session messages={session.messages}")

            # 调用API获取回复
            reply_content = self.reply_text(session, session_id)

            logger.debug(
                f"[OpenAIProxy] session_id={session_id}, reply_content={reply_content['content']}, "
                f"completion_tokens={reply_content['completion_tokens']}"
            )

            # 处理回复结果
            if reply_content["completion_tokens"] == 0 and len(reply_content["content"]) > 0:
                reply = Reply(ReplyType.ERROR, reply_content["content"])
            elif reply_content["completion_tokens"] > 0:
                self.sessions.session_reply(
                    reply_content["content"],
                    session_id,
                    reply_content["total_tokens"]
                )
                reply = Reply(ReplyType.TEXT, reply_content["content"])
            else:
                reply = Reply(ReplyType.ERROR, reply_content["content"])
                logger.debug(f"[OpenAIProxy] reply used 0 tokens: {reply_content}")

            return reply

        else:
            reply = Reply(ReplyType.ERROR, f"Bot不支持处理{context.type}类型的消息")
            return reply

    def reply_text(self, session: ChatGPTSession, session_id: str, retry_count=0) -> dict:
        """
        调用OpenAI Proxy API获取文本回复

        Args:
            session: 会话对象
            session_id: 会话ID
            retry_count: 重试次数

        Returns:
            包含回复内容和token信息的字典
        """
        try:
            # 过滤掉空的system message（gemini等模型不支持空system message）
            messages = [
                msg for msg in session.messages
                if not (msg.get('role') == 'system' and not msg.get('content', '').strip())
            ]

            # 调用API
            response = self.client.chat_completion(
                model=self.args["model"],
                messages=messages,
                temperature=self.args["temperature"],
                top_p=self.args["top_p"],
                max_tokens=self.args.get("max_tokens"),
                stream=False
            )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"API请求失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误信息: {error_data.get('error', {}).get('message', '未知错误')}"
                except:
                    error_msg += f", 响应内容: {response.text}"

                logger.error(f"[OpenAIProxy] {error_msg}")
                return {
                    "total_tokens": 0,
                    "completion_tokens": 0,
                    "content": error_msg
                }

            # 解析响应
            result = response.json()

            # 提取回复内容
            content = result["choices"][0]["message"]["content"]
            total_tokens = result.get("usage", {}).get("total_tokens", 0)
            completion_tokens = result.get("usage", {}).get("completion_tokens", 0)

            logger.info(f"[OpenAIProxy] reply={content[:100]}..., total_tokens={total_tokens}")

            return {
                "total_tokens": total_tokens,
                "completion_tokens": completion_tokens,
                "content": content
            }

        except Exception as e:
            need_retry = retry_count < 2
            error_msg = f"API调用异常: {str(e)}"

            logger.error(f"[OpenAIProxy] {error_msg}")

            if need_retry:
                logger.warn(f"[OpenAIProxy] 第{retry_count + 1}次重试")
                import time
                time.sleep(3)
                return self.reply_text(session, session_id, retry_count + 1)
            else:
                return {
                    "total_tokens": 0,
                    "completion_tokens": 0,
                    "content": error_msg
                }

    def _enhance_image_prompt(self, query: str) -> str:
        """
        优化图片生成prompt
        将简单的中文描述转换为详细的英文prompt，提高生成质量

        Args:
            query: 原始中文描述

        Returns:
            优化后的英文prompt
        """
        try:
            # 如果已经是较长的英文prompt，直接返回
            if len(query) > 50 and any(c.isalpha() and ord(c) < 128 for c in query):
                return query

            # 使用GPT模型优化prompt
            optimize_messages = [{
                "role": "system",
                "content": "你是一个专业的AI图像生成prompt优化助手。将用户的简单描述转换为详细、专业的英文prompt，适用于FLUX、Stable Diffusion等图像生成模型。"
            }, {
                "role": "user",
                "content": f"请将以下描述转换为详细的英文图像生成prompt（只返回英文prompt，不要解释）：\n{query}\n\n要求：\n1. 详细描述主体、风格、光影、构图\n2. 使用专业摄影和艺术术语\n3. 控制在100字以内\n4. 只返回英文prompt"
            }]

            response = self.client.chat_completion(
                model=self.model,
                messages=optimize_messages,
                temperature=0.7,
                max_tokens=200,
                stream=False
            )

            if response.status_code == 200:
                result = response.json()
                enhanced = result["choices"][0]["message"]["content"].strip()
                # 移除可能的引号
                enhanced = enhanced.strip('"\'')
                return enhanced
            else:
                logger.warning(f"[OpenAIProxy] prompt优化失败，使用原始prompt")
                return query

        except Exception as e:
            logger.warning(f"[OpenAIProxy] prompt优化异常: {str(e)}，使用原始prompt")
            return query

    def _generate_image(self, query: str) -> Reply:
        """
        生成图片

        Args:
            query: 图片描述

        Returns:
            Reply对象
        """
        try:
            # 获取生图模型
            image_model = conf().get("image_generation_model", "dall-e-3")
            logger.info(f"[OpenAIProxy] 使用生图模型: {image_model}, prompt: {query[:100]}...")

            # 调用图片生成API（直接使用用户的原始prompt）
            response = self.client.image_generation(
                model=image_model,
                prompt=query,
                n=1,
                size="1024x1024"
            )

            if response.status_code != 200:
                error_msg = f"图片生成失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误: {error_data.get('error', {}).get('message', '未知错误')}"
                except:
                    error_msg += f", 响应: {response.text}"

                logger.error(f"[OpenAIProxy] {error_msg}")
                return Reply(ReplyType.ERROR, error_msg)

            # 解析响应
            result = response.json()

            # 尝试不同的响应格式
            image_url = None
            if "data" in result and len(result["data"]) > 0:
                # DALL-E格式
                image_url = result["data"][0].get("url")
            elif "images" in result and len(result["images"]) > 0:
                # 其他格式
                image_url = result["images"][0]

            if not image_url:
                logger.error(f"[OpenAIProxy] 无法从响应中提取图片URL: {result}")
                return Reply(ReplyType.ERROR, "图片生成成功但无法获取图片链接")

            logger.info(f"[OpenAIProxy] 图片生成成功: {image_url}")
            return Reply(ReplyType.IMAGE_URL, image_url)

        except Exception as e:
            logger.error(f"[OpenAIProxy] 图片生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"图片生成失败: {str(e)}")

    def _generate_video(self, query: str, context=None) -> Reply:
        """
        生成视频（支持文生视频和图生视频）

        Args:
            query: 视频描述
            context: 上下文信息（用于获取引用的图片）

        Returns:
            Reply对象
        """
        try:
            # 获取视频生成配置
            video_model = conf().get("video_generation_model", "Grok-3")
            duration = conf().get("video_duration", 5)
            aspect_ratio = conf().get("video_aspect_ratio", "16:9")

            logger.info(f"[OpenAIProxy] 使用视频生成模型: {video_model}, 时长: {duration}秒, 宽高比: {aspect_ratio}")

            # 检查是否有引用的图片（图生视频）
            image_url = None
            session_id = context.get("session_id") if context else None

            # 检查是否有缓存的图片（当用户发送图片后立即发送grok命令）
            if session_id and session_id in memory.USER_IMAGE_CACHE:
                cached_image = memory.USER_IMAGE_CACHE[session_id]
                image_path = cached_image.get("path")

                if image_path and os.path.exists(image_path):
                    logger.info(f"[OpenAIProxy] 检测到引用图片，执行图生视频: {image_path}")

                    # 读取图片并转换为base64
                    try:
                        with open(image_path, "rb") as image_file:
                            image_data = base64.b64encode(image_file.read()).decode('utf-8')

                        # 获取图片扩展名
                        ext = os.path.splitext(image_path)[1].lower()
                        mime_type = {
                            '.jpg': 'image/jpeg',
                            '.jpeg': 'image/jpeg',
                            '.png': 'image/png',
                            '.gif': 'image/gif',
                            '.webp': 'image/webp'
                        }.get(ext, 'image/jpeg')

                        # 构建data URL
                        image_url = f"data:{mime_type};base64,{image_data}"
                        logger.info(f"[OpenAIProxy] 图片已转换为base64格式，大小: {len(image_data)} 字符")

                        # 清除缓存
                        del memory.USER_IMAGE_CACHE[session_id]

                    except Exception as e:
                        logger.warning(f"[OpenAIProxy] 读取引用图片失败: {str(e)}，将执行文生视频")
                        image_url = None

            # 调用视频生成API
            if image_url:
                logger.info(f"[OpenAIProxy] 执行图生视频，提示词: {query[:100]}...")
                response = self.client.video_generation(
                    model=video_model,
                    prompt=query,
                    image_url=image_url,
                    duration=duration,
                    aspect_ratio=aspect_ratio
                )
            else:
                logger.info(f"[OpenAIProxy] 执行文生视频，提示词: {query[:100]}...")
                response = self.client.video_generation(
                    model=video_model,
                    prompt=query,
                    duration=duration,
                    aspect_ratio=aspect_ratio
                )

            # 检查响应状态
            if response.status_code != 200:
                error_msg = f"视频生成失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误: {error_data.get('error', {}).get('message', '未知错误')}"
                except:
                    error_msg += f", 响应: {response.text}"

                logger.error(f"[OpenAIProxy] {error_msg}")
                return Reply(ReplyType.ERROR, error_msg)

            # 解析响应
            result = response.json()

            # 提取视频URL（尝试不同的响应格式）
            video_url = None
            if "data" in result and len(result["data"]) > 0:
                # 标准格式
                video_url = result["data"][0].get("url")
            elif "videos" in result and len(result["videos"]) > 0:
                # 其他格式
                video_url = result["videos"][0]
            elif "url" in result:
                # 直接URL格式
                video_url = result["url"]

            if not video_url:
                logger.error(f"[OpenAIProxy] 无法从响应中提取视频URL: {result}")
                return Reply(ReplyType.ERROR, "视频生成成功但无法获取视频链接")

            logger.info(f"[OpenAIProxy] 视频生成成功: {video_url}")
            return Reply(ReplyType.VIDEO_URL, video_url)

        except Exception as e:
            logger.error(f"[OpenAIProxy] 视频生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"视频生成失败: {str(e)}")
