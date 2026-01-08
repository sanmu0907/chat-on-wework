# encoding:utf-8
"""
即梦AI插件 - 支持图片和视频生成
支持魔搭社区和Gemini图片生成
"""

import json
import os
import io
import requests
import time
import tempfile
import threading
import random
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *
from config import conf


@plugins.register(
    name="Jimeng",
    desire_priority=90,
    hidden=False,
    desc="即梦AI图片和视频生成插件",
    version="1.0",
    author="Assistant",
)
class Jimeng(Plugin):
    def __init__(self):
        super().__init__()
        try:
            # 加载配置
            self.config = super().load_config()
            if not self.config:
                self.config = self._load_config_template()

            # 获取配置项 - 即梦
            self.enabled = self.config.get("enabled", False)
            self.api_base = self.config.get("jimeng_api_base", "http://113.45.68.49:8008")
            self.session_id = self.config.get("jimeng_session_id", "")
            self.image_model = self.config.get("jimeng_image_model", "jimeng-4.0")
            self.video_model = self.config.get("jimeng_video_model", "jimeng-video-3.0")
            self.image_size = self.config.get("jimeng_image_size", "1:1")
            self.video_resolution = self.config.get("jimeng_video_resolution", "1080p")
            self.cache_dir = self.config.get("cache_dir", "tmp/jimeng_cache")
            self.cache_expire_hours = self.config.get("cache_expire_hours", 24)

            # 获取配置项 - 魔搭社区
            self.moda_api_url = self.config.get("moda_api_url", "https://api-inference.modelscope.cn/")
            self.moda_api_key = self.config.get("moda_api_key", "")
            self.moda_model = self.config.get("moda_model", "Qwen/Qwen-Image")
            self.moda_seed = self.config.get("moda_seed", "随机")

            # 获取配置项 - 智谱AI
            self.zhipu_api_key = self.config.get("zhipu_api_key", "")
            self.zhipu_model = self.config.get("zhipu_model", "cogview-4")
            self.zhipu_size = self.config.get("zhipu_size", "1024x1024")
            self.zhipu_quality = self.config.get("zhipu_quality", "standard")

            # 获取配置项 - Gemini（使用项目全局配置的图片生成模型）
            self.gemini_api_key = conf().get("open_ai_api_key", "")
            self.gemini_api_base = conf().get("open_ai_api_base", "https://api.openai.com/v1")
            self.gemini_model = conf().get("image_generation_model", "FLUX.1-schnell")

            # 创建缓存目录
            if not os.path.isabs(self.cache_dir):
                # 如果是相对路径，使用项目根目录
                from config import get_root
                self.cache_dir = os.path.join(get_root(), self.cache_dir)

            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"[Jimeng] 缓存目录: {self.cache_dir}")

            # 检查配置
            if not self.session_id:
                logger.warn("[Jimeng] jimeng_session_id未配置，即梦功能将不会生效")
            if not self.moda_api_key:
                logger.warn("[Jimeng] moda_api_key未配置，魔搭功能将不会生效")
            if not self.zhipu_api_key:
                logger.warn("[Jimeng] zhipu_api_key未配置，智谱功能将不会生效")
            if not self.gemini_api_key:
                logger.warn("[Jimeng] open_ai_api_key未配置，通义功能将不会生效")

            # 注册事件处理器
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

            # 启动缓存清理线程
            self._start_cache_cleanup_thread()

            logger.info(f"[Jimeng] 插件初始化成功, enabled={self.enabled}")
            logger.info(f"[Jimeng] 即梦API: {self.api_base}")
            logger.info(f"[Jimeng] 魔搭API: {self.moda_api_url}, 模型: {self.moda_model}")
            logger.info(f"[Jimeng] 智谱AI: 模型: {self.zhipu_model}")
            logger.info(f"[Jimeng] z-image API: {self.gemini_api_base}, 模型: {self.gemini_model}")

        except Exception as e:
            logger.error(f"[Jimeng] 初始化异常: {e}")
            raise Exception("[Jimeng] init failed, ignore")

    def on_handle_context(self, e_context: EventContext):
        """处理消息事件"""
        if not self.enabled:
            return

        context = e_context["context"]

        # 只处理文本消息
        if context.type != ContextType.TEXT:
            return

        content = context.content

        # 检查是否包含关键词
        has_jimeng_cn = "即梦" in content  # 中文关键词 -> 生成图片
        has_jimeng_en = "jimeng" in content.lower()  # 英文关键词 -> 生成视频
        has_moda = "魔搭" in content  # 魔搭关键词 -> 魔搭生图
        has_zhipu = "智谱" in content  # 智谱关键词 -> 智谱生图
        has_tongyi = "通义" in content  # 通义关键词 -> z-image生图

        if not (has_jimeng_cn or has_jimeng_en or has_moda or has_zhipu or has_tongyi):
            return

        # 确定生成类型和关键词
        if has_zhipu:
            generation_type = "zhipu"
            keyword = "智谱"
        elif has_tongyi:
            generation_type = "gemini"
            keyword = "通义"
        elif has_moda:
            generation_type = "moda"
            keyword = "魔搭"
        elif has_jimeng_en:
            generation_type = "video"
            keyword = "jimeng"
        else:
            generation_type = "image"
            keyword = "即梦"

        logger.info(f"[Jimeng] 检测到关键词 '{keyword}': {content}")

        try:
            # 移除关键词，获取实际的prompt
            if generation_type == "video":
                prompt = content.replace("jimeng", "", 1).replace("Jimeng", "", 1).replace("JIMENG", "", 1).strip()
            elif generation_type == "moda":
                prompt = content.replace("魔搭", "", 1).strip()
            elif generation_type == "zhipu":
                prompt = content.replace("智谱", "", 1).strip()
            elif generation_type == "gemini":
                prompt = content.replace("通义", "", 1).strip()
            else:
                prompt = content.replace("即梦", "", 1).strip()

            # 检测是否是引用消息格式
            # 格式: "「用户名：原文内容」\n- - - - - - - - - - - - - - -\n即梦"
            import re
            quote_pattern = r'^「[^：]+：(.+?)」\s*\n[-\s]+\n(.*)$'
            quote_match = re.match(quote_pattern, content, re.DOTALL)

            if quote_match:
                # 提取被引用的原文
                quoted_content = quote_match.group(1).strip()
                # 提取引用后的文本
                after_quote = quote_match.group(2).strip()

                # 如果引用后的文本只是关键词，使用引用的内容作为prompt
                if after_quote in [keyword, ""]:
                    prompt = quoted_content
                else:
                    # 否则，移除关键词后使用剩余内容
                    if generation_type == "video":
                        prompt = after_quote.replace("jimeng", "", 1).replace("Jimeng", "", 1).replace("JIMENG", "", 1).strip()
                    elif generation_type == "moda":
                        prompt = after_quote.replace("魔搭", "", 1).strip()
                    elif generation_type == "zhipu":
                        prompt = after_quote.replace("智谱", "", 1).strip()
                    elif generation_type == "gemini":
                        prompt = after_quote.replace("通义", "", 1).strip()
                    else:
                        prompt = after_quote.replace("即梦", "", 1).strip()
                    if not prompt:
                        prompt = quoted_content

                logger.info(f"[Jimeng] 检测到引用消息，提取内容: {quoted_content[:50]}...")

            # 如果prompt为空，返回提示
            if not prompt:
                reply = Reply(ReplyType.TEXT, f"请在{keyword}后面输入要生成的内容描述")
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

            # 根据生成类型调用相应方法
            if generation_type == "video":
                # 生成视频
                logger.info(f"[Jimeng] 准备生成视频: {prompt[:100]}...")
                reply = self._generate_video(prompt)
            elif generation_type == "moda":
                # 魔搭生成图片
                logger.info(f"[Jimeng] 准备使用魔搭生成图片: {prompt[:100]}...")
                reply = self._generate_moda_image(prompt)
            elif generation_type == "zhipu":
                # 智谱生成图片
                logger.info(f"[Jimeng] 准备使用智谱生成图片: {prompt[:100]}...")
                reply = self._generate_zhipu_image(prompt)
            elif generation_type == "gemini":
                # z-image生成图片
                logger.info(f"[Jimeng] 准备使用z-image生成图片: {prompt[:100]}...")
                reply = self._generate_gemini_image(prompt)
            else:
                # 即梦生成图片
                logger.info(f"[Jimeng] 准备生成图片: {prompt[:100]}...")
                reply = self._generate_image(prompt)

            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

        except Exception as e:
            logger.error(f"[Jimeng] 处理失败: {e}")
            reply = Reply(ReplyType.ERROR, f"即梦AI处理失败: {str(e)}")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

    def _generate_image(self, prompt: str) -> Reply:
        """
        生成图片

        Args:
            prompt: 图片描述

        Returns:
            Reply对象
        """
        try:
            logger.info(f"[Jimeng] 开始生成图片，模型: {self.image_model}, prompt: {prompt[:100]}...")
            start_time = time.time()

            url = f"{self.api_base}/v1/images/generations"
            headers = {
                "Authorization": f"Bearer {self.session_id}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.image_model,
                "prompt": prompt,
                "size": self.image_size,
                "n": 1
            }

            response = requests.post(url, headers=headers, json=payload, timeout=120)
            api_time = time.time() - start_time
            logger.info(f"[Jimeng] 图片API调用完成，耗时: {api_time:.2f}秒")

            if response.status_code != 200:
                error_msg = f"图片生成失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误: {error_data.get('error', {}).get('message', '未知错误')}"
                except:
                    error_msg += f", 响应: {response.text}"

                logger.error(f"[Jimeng] {error_msg}")
                return Reply(ReplyType.ERROR, error_msg)

            # 解析响应
            result = response.json()
            logger.debug(f"[Jimeng] API返回结果: {result}")

            # 提取图片URL
            image_url = None
            if "data" in result and result["data"] and len(result["data"]) > 0:
                image_url = result["data"][0].get("url")

            if not image_url:
                logger.error(f"[Jimeng] 无法从响应中提取图片URL: {result}")
                return Reply(ReplyType.ERROR, "图片生成成功但无法获取图片链接")

            logger.info(f"[Jimeng] 图片生成成功，正在下载: {image_url}")

            # 下载图片到本地
            local_path = self._download_file(image_url, "image", timeout=120)

            if not local_path:
                return Reply(ReplyType.ERROR, "图片下载失败")

            logger.info(f"[Jimeng] 图片已保存到: {local_path}")

            # 读取文件并返回文件对象
            try:
                with open(local_path, 'rb') as f:
                    image_storage = io.BytesIO(f.read())
                image_storage.seek(0)
                return Reply(ReplyType.IMAGE, image_storage)
            except Exception as e:
                logger.error(f"[Jimeng] 读取图片文件失败: {str(e)}")
                return Reply(ReplyType.ERROR, f"读取图片文件失败: {str(e)}")

        except Exception as e:
            logger.error(f"[Jimeng] 图片生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"图片生成失败: {str(e)}")

    def _generate_video(self, prompt: str) -> Reply:
        """
        生成视频

        Args:
            prompt: 视频描述

        Returns:
            Reply对象
        """
        try:
            logger.info(f"[Jimeng] 开始生成视频，模型: {self.video_model}, prompt: {prompt[:100]}...")
            start_time = time.time()

            url = f"{self.api_base}/v1/videos/generations"
            headers = {
                "Authorization": f"Bearer {self.session_id}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.video_model,
                "prompt": prompt,
                "resolution": self.video_resolution,
                "n": 1
            }

            response = requests.post(url, headers=headers, json=payload, timeout=600)
            api_time = time.time() - start_time
            logger.info(f"[Jimeng] 视频API调用完成，耗时: {api_time:.2f}秒")

            if response.status_code != 200:
                error_msg = f"视频生成失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误: {error_data.get('error', {}).get('message', '未知错误')}"
                except:
                    error_msg += f", 响应: {response.text}"

                logger.error(f"[Jimeng] {error_msg}")
                return Reply(ReplyType.ERROR, error_msg)

            # 解析响应
            result = response.json()
            logger.debug(f"[Jimeng] 视频API返回结果: {result}")

            # 提取视频URL
            video_url = None
            if "data" in result and result["data"] and len(result["data"]) > 0:
                video_url = result["data"][0].get("url")
            elif "videos" in result and len(result["videos"]) > 0:
                video_url = result["videos"][0]

            if not video_url:
                logger.error(f"[Jimeng] 无法从响应中提取视频URL: {result}")
                return Reply(ReplyType.ERROR, "视频生成成功但无法获取视频链接")

            logger.info(f"[Jimeng] 视频生成成功，正在下载: {video_url}")

            # 下载视频到本地
            local_path = self._download_file(video_url, "video", timeout=300)

            if not local_path:
                return Reply(ReplyType.ERROR, "视频下载失败")

            logger.info(f"[Jimeng] 视频已保存到: {local_path}")

            # 读取文件并返回文件对象
            try:
                with open(local_path, 'rb') as f:
                    video_storage = io.BytesIO(f.read())
                video_storage.seek(0)
                return Reply(ReplyType.VIDEO, video_storage)
            except Exception as e:
                logger.error(f"[Jimeng] 读取视频文件失败: {str(e)}")
                return Reply(ReplyType.ERROR, f"读取视频文件失败: {str(e)}")

        except Exception as e:
            logger.error(f"[Jimeng] 视频生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"视频生成失败: {str(e)}")

    def _generate_moda_image(self, prompt: str) -> Reply:
        """
        使用魔搭社区API生成图片

        Args:
            prompt: 图片描述

        Returns:
            Reply对象
        """
        try:
            logger.info(f"[Jimeng] 开始使用魔搭生成图片，模型: {self.moda_model}, prompt: {prompt[:100]}...")
            start_time = time.time()

            # 生成随机seed
            if self.moda_seed == "随机" or not self.moda_seed:
                current_seed = random.randint(1, 2147483647)
            else:
                try:
                    current_seed = int(self.moda_seed)
                except (ValueError, TypeError):
                    current_seed = random.randint(1, 2147483647)

            # 提交任务
            task_url = f"{self.moda_api_url}v1/images/generations"
            headers = {
                "Authorization": f"Bearer {self.moda_api_key}",
                "Content-Type": "application/json",
                "X-ModelScope-Async-Mode": "true"
            }

            payload = {
                "model": self.moda_model,
                "prompt": prompt,
                "seed": current_seed
            }

            response = requests.post(task_url, headers=headers, json=payload, timeout=30)
            if response.status_code != 200:
                error_msg = f"魔搭任务提交失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误: {error_data}"
                except:
                    error_msg += f", 响应: {response.text}"
                logger.error(f"[Jimeng] {error_msg}")
                return Reply(ReplyType.ERROR, error_msg)

            task_response = response.json()
            task_id = task_response.get("task_id")

            if not task_id:
                logger.error(f"[Jimeng] 未能获取任务ID: {task_response}")
                return Reply(ReplyType.ERROR, "魔搭图片生成失败：未能获取任务ID")

            logger.info(f"[Jimeng] 魔搭任务已提交，task_id: {task_id}，开始轮询...")

            # 轮询任务结果（指数退避策略）
            delay = 1
            max_delay = 10
            max_retries = 60  # 最多轮询60次
            retry_count = 0

            query_headers = {
                "Authorization": f"Bearer {self.moda_api_key}",
                "Content-Type": "application/json",
                "X-ModelScope-Task-Type": "image_generation"
            }

            while retry_count < max_retries:
                time.sleep(delay)
                retry_count += 1

                query_url = f"{self.moda_api_url}v1/tasks/{task_id}"
                result_response = requests.get(query_url, headers=query_headers, timeout=30)

                if result_response.status_code != 200:
                    logger.warning(f"[Jimeng] 查询任务状态失败，状态码: {result_response.status_code}")
                    delay = min(delay * 2, max_delay)
                    continue

                data = result_response.json()
                task_status = data.get("task_status")
                logger.debug(f"[Jimeng] 任务状态: {task_status}, 重试次数: {retry_count}")

                if task_status == "SUCCEED":
                    output_images = data.get("output_images", [])
                    if not output_images:
                        logger.error(f"[Jimeng] 图片生成成功但未返回图片URL: {data}")
                        return Reply(ReplyType.ERROR, "魔搭图片生成成功但未返回图片URL")

                    image_url = output_images[0]
                    api_time = time.time() - start_time
                    logger.info(f"[Jimeng] 魔搭图片生成成功，总耗时: {api_time:.2f}秒，seed: {current_seed}")

                    # 下载图片
                    local_path = self._download_file(image_url, "moda_image", timeout=120)
                    if not local_path:
                        return Reply(ReplyType.ERROR, "魔搭图片下载失败")

                    # 读取文件并返回
                    try:
                        with open(local_path, 'rb') as f:
                            image_storage = io.BytesIO(f.read())
                        image_storage.seek(0)
                        return Reply(ReplyType.IMAGE, image_storage)
                    except Exception as e:
                        logger.error(f"[Jimeng] 读取魔搭图片文件失败: {str(e)}")
                        return Reply(ReplyType.ERROR, f"读取图片文件失败: {str(e)}")

                elif task_status == "FAILED":
                    logger.error(f"[Jimeng] 魔搭图片生成失败: {data}")
                    return Reply(ReplyType.ERROR, "魔搭图片生成失败")

                # 指数退避
                delay = min(delay * 2, max_delay)

            # 超时
            logger.error(f"[Jimeng] 魔搭图片生成超时，已重试{retry_count}次")
            return Reply(ReplyType.ERROR, "魔搭图片生成超时")

        except Exception as e:
            logger.error(f"[Jimeng] 魔搭图片生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"魔搭图片生成失败: {str(e)}")

    def _generate_gemini_image(self, prompt: str) -> Reply:
        """
        使用z-image模型生成图片（OpenAI兼容API生图）

        Args:
            prompt: 图片描述

        Returns:
            Reply对象
        """
        try:
            logger.info(f"[Jimeng] 开始使用z-image生成图片，模型: {self.gemini_model}, prompt: {prompt[:100]}...")
            start_time = time.time()

            url = f"{self.gemini_api_base}/images/generations"
            headers = {
                "Authorization": f"Bearer {self.gemini_api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": self.gemini_model,
                "prompt": prompt,
                "n": 1,
                "size": "1024x1024"
            }

            response = requests.post(url, headers=headers, json=payload, timeout=120)
            api_time = time.time() - start_time
            logger.info(f"[Jimeng] z-image API调用完成，耗时: {api_time:.2f}秒")

            if response.status_code != 200:
                error_msg = f"z-image图片生成失败，状态码: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f", 错误: {error_data.get('error', {}).get('message', '未知错误')}"
                except:
                    error_msg += f", 响应: {response.text}"

                logger.error(f"[Jimeng] {error_msg}")
                return Reply(ReplyType.ERROR, error_msg)

            # 解析响应
            result = response.json()
            logger.debug(f"[Jimeng] z-image API返回结果: {result}")

            # 提取图片URL - 支持多种响应格式
            image_url = None

            # 格式1: images[].url (z-image格式)
            if "images" in result and result["images"] and len(result["images"]) > 0:
                image_url = result["images"][0].get("url")
            # 格式2: data[].url (通用格式)
            elif "data" in result and result["data"] and len(result["data"]) > 0:
                image_url = result["data"][0].get("url")

            if not image_url:
                logger.error(f"[Jimeng] 无法从响应中提取图片URL: {result}")
                return Reply(ReplyType.ERROR, "z-image图片生成成功但无法获取图片链接")

            logger.info(f"[Jimeng] z-image图片生成成功，正在下载: {image_url}")

            # 下载图片到本地
            local_path = self._download_file(image_url, "zimage", timeout=120)

            if not local_path:
                return Reply(ReplyType.ERROR, "z-image图片下载失败")

            logger.info(f"[Jimeng] z-image图片已保存到: {local_path}")

            # 读取文件并返回文件对象
            try:
                with open(local_path, 'rb') as f:
                    image_storage = io.BytesIO(f.read())
                image_storage.seek(0)
                return Reply(ReplyType.IMAGE, image_storage)
            except Exception as e:
                logger.error(f"[Jimeng] 读取z-image图片文件失败: {str(e)}")
                return Reply(ReplyType.ERROR, f"读取图片文件失败: {str(e)}")

        except Exception as e:
            logger.error(f"[Jimeng] z-image图片生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"z-image图片生成失败: {str(e)}")

    def _generate_zhipu_image(self, prompt: str) -> Reply:
        """
        使用智谱AI生成图片

        Args:
            prompt: 图片描述

        Returns:
            Reply对象
        """
        try:
            if not self.zhipu_api_key:
                return Reply(ReplyType.ERROR, "智谱API Key未配置，请在配置文件中填写zhipu_api_key")

            logger.info(f"[Jimeng] 开始使用智谱AI生成图片，模型: {self.zhipu_model}, prompt: {prompt[:100]}...")
            start_time = time.time()

            # 导入智谱AI SDK
            from zhipuai import ZhipuAI

            # 初始化客户端
            client = ZhipuAI(api_key=self.zhipu_api_key)

            # 调用图片生成API
            response = client.images.generations(
                model=self.zhipu_model,
                prompt=prompt,
                size=self.zhipu_size,
                quality=self.zhipu_quality,
            )

            api_time = time.time() - start_time
            logger.info(f"[Jimeng] 智谱AI API调用完成，耗时: {api_time:.2f}秒")

            if not response or not response.data or len(response.data) == 0:
                logger.error("[Jimeng] 智谱AI响应为空或没有返回图片数据")
                return Reply(ReplyType.ERROR, "智谱AI图片生成失败：响应为空")

            # 获取图片URL
            image_url = response.data[0].url
            logger.info(f"[Jimeng] 智谱AI图片生成成功，正在下载: {image_url}")

            # 下载图片到本地
            local_path = self._download_file(image_url, "zhipu_image", timeout=120)

            if not local_path:
                return Reply(ReplyType.ERROR, "智谱AI图片下载失败")

            logger.info(f"[Jimeng] 智谱AI图片已保存到: {local_path}")

            # 读取文件并返回文件对象
            try:
                with open(local_path, 'rb') as f:
                    image_storage = io.BytesIO(f.read())
                image_storage.seek(0)
                return Reply(ReplyType.IMAGE, image_storage)
            except Exception as e:
                logger.error(f"[Jimeng] 读取智谱AI图片文件失败: {str(e)}")
                return Reply(ReplyType.ERROR, f"读取图片文件失败: {str(e)}")

        except Exception as e:
            logger.error(f"[Jimeng] 智谱AI图片生成异常: {str(e)}")
            return Reply(ReplyType.ERROR, f"智谱AI图片生成失败: {str(e)}")

    def get_help_text(self, **kwargs):
        """获取帮助文本"""
        help_text = "即梦AI插件\n"
        help_text += "触发词：\n"
        help_text += "  - 即梦（生成图片）\n"
        help_text += "  - jimeng（生成视频）\n"
        help_text += "  - 魔搭（魔搭社区生图，需有效API key）\n"
        help_text += "  - 智谱（智谱AI生图，需有效API key）\n"
        help_text += "  - 通义（z-image快速生图）\n\n"
        help_text += "使用方法：\n"
        help_text += "1. 即梦生图：即梦 一只可爱的小猫\n"
        help_text += "2. 生成视频：jimeng 一只狗在跑步\n"
        help_text += "3. 魔搭生图：魔搭 科幻未来城市\n"
        help_text += "4. 智谱生图：智谱 夕阳下的海滩\n"
        help_text += "5. z-image生图：通义 赛博朋克街景\n"
        help_text += "6. 引用消息生成：引用一条消息后回复关键词\n"
        return help_text

    def _download_file(self, url: str, file_type: str, timeout: int = 60) -> str:
        """
        下载文件到本地缓存目录

        Args:
            url: 文件URL
            file_type: 文件类型（image或video）
            timeout: 下载超时时间（秒）

        Returns:
            本地文件路径，失败返回None
        """
        try:
            # 下载文件
            logger.info(f"[Jimeng] 开始下载{file_type}，超时设置: {timeout}秒")
            download_start = time.time()
            response = requests.get(url, timeout=timeout, stream=True)
            if response.status_code != 200:
                logger.error(f"[Jimeng] 下载文件失败，状态码: {response.status_code}")
                return None

            # 确定文件扩展名
            if file_type == "image":
                # 从URL或Content-Type推断扩展名
                ext = ".jpg"
                content_type = response.headers.get("Content-Type", "")
                if "png" in content_type:
                    ext = ".png"
                elif "webp" in content_type:
                    ext = ".webp"
            else:  # video
                ext = ".mp4"
                content_type = response.headers.get("Content-Type", "")
                if "webm" in content_type:
                    ext = ".webm"

            # 生成文件名（使用时间戳）
            timestamp = int(time.time() * 1000)
            filename = f"jimeng_{file_type}_{timestamp}{ext}"
            filepath = os.path.join(self.cache_dir, filename)

            # 保存文件
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            download_time = time.time() - download_start
            file_size = os.path.getsize(filepath)
            logger.info(f"[Jimeng] 文件已下载: {filepath}, 大小: {file_size} bytes ({file_size/1024/1024:.2f} MB), 耗时: {download_time:.2f}秒")
            return filepath

        except Exception as e:
            logger.error(f"[Jimeng] 下载文件异常: {str(e)}")
            return None

    def _start_cache_cleanup_thread(self):
        """启动缓存清理线程"""
        def cleanup_worker():
            while True:
                try:
                    # 每小时清理一次
                    time.sleep(3600)
                    self._cleanup_cache()
                except Exception as e:
                    logger.error(f"[Jimeng] 缓存清理异常: {str(e)}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("[Jimeng] 缓存清理线程已启动")

    def _cleanup_cache(self):
        """清理过期的缓存文件"""
        try:
            if not os.path.exists(self.cache_dir):
                return

            current_time = time.time()
            expire_seconds = self.cache_expire_hours * 3600
            deleted_count = 0
            total_size = 0

            for filename in os.listdir(self.cache_dir):
                filepath = os.path.join(self.cache_dir, filename)

                # 跳过目录
                if os.path.isdir(filepath):
                    continue

                # 检查文件年龄
                file_age = current_time - os.path.getmtime(filepath)

                if file_age > expire_seconds:
                    file_size = os.path.getsize(filepath)
                    os.remove(filepath)
                    deleted_count += 1
                    total_size += file_size
                    logger.debug(f"[Jimeng] 删除过期文件: {filename}, 年龄: {file_age/3600:.1f}小时")

            if deleted_count > 0:
                logger.info(f"[Jimeng] 缓存清理完成: 删除 {deleted_count} 个文件, 释放 {total_size/1024/1024:.2f} MB空间")
            else:
                logger.debug("[Jimeng] 缓存清理完成: 无过期文件")

        except Exception as e:
            logger.error(f"[Jimeng] 清理缓存异常: {str(e)}")

    def _load_config_template(self):
        """加载配置模板"""
        logger.debug("[Jimeng] 未找到config.json，使用config.json.template")
        try:
            plugin_config_path = os.path.join(self.path, "config.json.template")
            if os.path.exists(plugin_config_path):
                with open(plugin_config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.exception(e)
        return {}
