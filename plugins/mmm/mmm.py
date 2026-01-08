# encoding:utf-8
"""
MMM美图插件 - 支持多种美图类型
"""

import json
import os
import random
import requests
import tempfile
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *


@plugins.register(
    name="MMM",
    desire_priority=85,
    hidden=False,
    desc="美图视频插件，支持美女、黑丝、JK、白丝、诱惑等多种图片，以及黑丝视频、白丝视频、清纯视频等",
    version="1.0",
    author="Assistant",
)
class MMM(Plugin):
    def __init__(self):
        super().__init__()
        try:
            # 加载配置
            self.config = super().load_config()
            if not self.config:
                logger.warn("[MMM] 配置文件不存在或为空，使用默认配置")
                self.config = self._get_default_config()

            # 获取配置项
            self.enabled = self.config.get("enabled", False)
            self.triggers = self.config.get("triggers", {})
            self.video_triggers = self.config.get("video_triggers", {})
            self.image_apis = self.config.get("image_apis", {})
            self.video_apis = self.config.get("video_apis", {})
            self.settings = self.config.get("settings", {})

            # 设置
            self.timeout = self.settings.get("timeout", 10)
            self.max_redirects = self.settings.get("max_redirects", 3)
            self.cache_dir = self.settings.get("cache_dir", "tmp/mmm_cache")
            self.video_max_size_mb = self.settings.get("video_max_size_mb", 30)

            # 创建缓存目录
            if not os.path.isabs(self.cache_dir):
                from config import get_root
                self.cache_dir = os.path.join(get_root(), self.cache_dir)

            os.makedirs(self.cache_dir, exist_ok=True)
            logger.info(f"[MMM] 缓存目录: {self.cache_dir}")

            # 注册事件处理器
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context

            logger.info(f"[MMM] 插件初始化成功, enabled={self.enabled}")

        except Exception as e:
            logger.error(f"[MMM] 初始化异常: {e}")
            raise Exception("[MMM] init failed, ignore")

    def _get_default_config(self):
        """获取默认配置"""
        return {
            "enabled": False,
            "triggers": {
                "美女": ["美女", "666", "妹子"],
                "黑丝": ["黑丝"],
                "JK": ["jk", "JK"],
                "白丝": ["白丝"],
                "诱惑": ["诱惑", "性感"]
            },
            "image_apis": {
                "美女": [
                    "https://api.btstu.cn/sjbz/api.php?lx=dongman&format=images&method=mobile&lx=meizi",
                    "https://cdn.seovx.com/?mom=302",
                    "https://api.mhimg.cn/api/girls_img/?type=img",
                    "https://api.mhimg.cn/api/Welfare_img/"
                ],
                "黑丝": "http://api.yujn.cn/api/heisi.php",
                "JK": "http://api.yujn.cn/api/jk.php",
                "白丝": "http://api.yujn.cn/api/baisi.php",
                "诱惑": "http://api.yujn.cn/api/yht.php"
            },
            "settings": {
                "timeout": 10,
                "max_redirects": 3,
                "cache_dir": "tmp/mmm_cache"
            }
        }

    def on_handle_context(self, e_context: EventContext):
        """处理消息事件"""
        if not self.enabled:
            return

        context = e_context["context"]

        # 只处理文本消息
        if context.type != ContextType.TEXT:
            return

        content = context.content.strip()

        # 先检查视频触发关键词（优先级更高，因为更具体）
        matched_type = None
        matched_media_type = None

        for video_type, keywords in self.video_triggers.items():
            for keyword in keywords:
                if keyword.lower() in content.lower():
                    matched_type = video_type
                    matched_media_type = "video"
                    logger.info(f"[MMM] 检测到视频关键词 '{keyword}' (类型: {video_type}): {content}")
                    break
            if matched_type:
                break

        # 如果没有匹配到视频，再检查图片触发关键词
        if not matched_type:
            for image_type, keywords in self.triggers.items():
                for keyword in keywords:
                    if keyword.lower() in content.lower():
                        matched_type = image_type
                        matched_media_type = "image"
                        logger.info(f"[MMM] 检测到图片关键词 '{keyword}' (类型: {image_type}): {content}")
                        break
                if matched_type:
                    break

        if not matched_type:
            return

        try:
            # 根据类型获取图片或视频
            if matched_media_type == "video":
                reply = self._fetch_video(matched_type)
            else:
                reply = self._fetch_image(matched_type)

            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

        except Exception as e:
            logger.error(f"[MMM] 处理消息异常: {e}")
            reply = Reply(ReplyType.ERROR, f"获取{matched_type}失败: {str(e)}")
            e_context["reply"] = reply
            e_context.action = EventAction.BREAK_PASS

    def _fetch_image(self, image_type):
        """获取指定类型的图片"""
        apis = self.image_apis.get(image_type)

        if not apis:
            return Reply(ReplyType.ERROR, f"未配置{image_type}图片API")

        # 如果APIs是列表，随机选择并尝试
        if isinstance(apis, list):
            # 随机打乱顺序尝试所有API
            api_list = apis.copy()
            random.shuffle(api_list)

            for api_url in api_list:
                try:
                    image_path = self._download_image_direct(api_url)
                    if image_path:
                        logger.info(f"[MMM] 成功获取{image_type}图片: {api_url}")
                        return Reply(ReplyType.IMAGE, image_path)
                except Exception as e:
                    logger.warning(f"[MMM] API请求失败 {api_url}: {e}")
                    continue

            return Reply(ReplyType.ERROR, f"{image_type}图片接口暂时不可用，请稍后再试")

        # 如果APIs是单个字符串
        else:
            try:
                # 先尝试直接下载
                image_path = self._download_image_with_redirect(apis)
                if image_path:
                    logger.info(f"[MMM] 成功获取{image_type}图片: {apis}")
                    return Reply(ReplyType.IMAGE, image_path)
                else:
                    return Reply(ReplyType.ERROR, f"{image_type}图片接口暂时不可用")
            except Exception as e:
                logger.error(f"[MMM] 获取{image_type}图片异常: {e}")
                return Reply(ReplyType.ERROR, f"获取{image_type}图片失败: {str(e)}")

    def _download_image_direct(self, url):
        """直接下载图片（用于返回图片流的API）"""
        try:
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=True,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # 检查是否是图片
                if content_type.startswith('image/'):
                    # 保存到临时文件
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix='.jpg',
                        dir=self.cache_dir
                    ) as tmp_file:
                        tmp_file.write(response.content)
                        return tmp_file.name

            return None

        except Exception as e:
            logger.debug(f"[MMM] 直接下载失败 {url}: {e}")
            return None

    def _download_image_with_redirect(self, url):
        """下载图片（处理重定向和JSON响应）"""
        try:
            # 首先尝试获取API响应
            response = requests.get(
                url,
                timeout=self.timeout,
                allow_redirects=False,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            # 处理重定向
            redirect_count = 0
            while response.status_code in [301, 302, 303, 307, 308] and redirect_count < self.max_redirects:
                redirect_url = response.headers.get('Location')
                if not redirect_url:
                    break

                logger.debug(f"[MMM] 重定向到: {redirect_url}")
                response = requests.get(
                    redirect_url,
                    timeout=self.timeout,
                    allow_redirects=False,
                    headers={'User-Agent': 'Mozilla/5.0'}
                )
                redirect_count += 1

            if response.status_code == 200:
                content_type = response.headers.get('Content-Type', '')

                # 如果返回的是JSON，提取图片URL
                if 'application/json' in content_type:
                    try:
                        data = response.json()
                        # 尝试多个可能的字段名
                        image_url = (data.get('data') or
                                   data.get('url') or
                                   data.get('image') or
                                   data.get('img') or
                                   data.get('imgurl'))

                        if image_url:
                            # 下载实际的图片
                            return self._download_image_direct(image_url)
                    except Exception as e:
                        logger.error(f"[MMM] 解析JSON响应失败: {e}")

                # 如果直接返回图片
                elif content_type.startswith('image/'):
                    with tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix='.jpg',
                        dir=self.cache_dir
                    ) as tmp_file:
                        tmp_file.write(response.content)
                        return tmp_file.name

            return None

        except Exception as e:
            logger.error(f"[MMM] 下载图片异常 {url}: {e}")
            return None

    def _fetch_video(self, video_type):
        """获取指定类型的视频"""
        api_url = self.video_apis.get(video_type)

        if not api_url:
            return Reply(ReplyType.ERROR, f"未配置{video_type}API")

        try:
            video_path = self._download_video(api_url)
            if video_path:
                logger.info(f"[MMM] 成功获取{video_type}: {api_url}")
                return Reply(ReplyType.VIDEO, video_path)
            else:
                return Reply(ReplyType.ERROR, f"{video_type}接口暂时不可用")
        except Exception as e:
            logger.error(f"[MMM] 获取{video_type}异常: {e}")
            return Reply(ReplyType.ERROR, f"获取{video_type}失败: {str(e)}")

    def _download_video(self, url):
        """下载视频（处理JSON响应）"""
        try:
            # 请求API获取视频URL
            response = requests.get(
                url,
                timeout=self.timeout,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code != 200:
                logger.error(f"[MMM] 视频API请求失败: {response.status_code}")
                return None

            content_type = response.headers.get('Content-Type', '')

            # 处理JSON响应
            if 'application/json' in content_type or url.endswith('type=json'):
                try:
                    data = response.json()
                    # 尝试多个可能的字段名
                    video_url = (data.get('data') or
                               data.get('url') or
                               data.get('video') or
                               data.get('video_url') or
                               data.get('mp4'))

                    if video_url:
                        logger.info(f"[MMM] 从JSON获取视频URL: {video_url}")
                        # 下载实际的视频文件
                        return self._download_video_file(video_url)
                    else:
                        logger.error(f"[MMM] JSON响应中未找到视频URL: {data}")
                        return None
                except Exception as e:
                    logger.error(f"[MMM] 解析视频JSON失败: {e}")
                    return None

            # 如果直接返回视频文件
            elif content_type.startswith('video/'):
                logger.info(f"[MMM] 直接获取到视频文件")
                with tempfile.NamedTemporaryFile(
                    delete=False,
                    suffix='.mp4',
                    dir=self.cache_dir
                ) as tmp_file:
                    tmp_file.write(response.content)
                    return tmp_file.name

            else:
                logger.error(f"[MMM] 未知的Content-Type: {content_type}")
                return None

        except Exception as e:
            logger.error(f"[MMM] 下载视频异常 {url}: {e}")
            return None

    def _download_video_file(self, url):
        """下载视频文件（带大小限制）"""
        try:
            logger.info(f"[MMM] 开始下载视频文件: {url}")
            response = requests.get(
                url,
                timeout=self.timeout * 3,  # 视频下载给更长的超时时间
                stream=True,
                headers={'User-Agent': 'Mozilla/5.0'}
            )

            if response.status_code != 200:
                logger.error(f"[MMM] 视频文件下载失败: {response.status_code}")
                return None

            # 检查文件大小
            content_length = response.headers.get('Content-Length')
            if content_length:
                size_mb = int(content_length) / (1024 * 1024)
                if size_mb > self.video_max_size_mb:
                    logger.warning(f"[MMM] 视频文件过大: {size_mb:.2f}MB > {self.video_max_size_mb}MB")
                    return None
                logger.info(f"[MMM] 视频文件大小: {size_mb:.2f}MB")

            # 下载视频
            total_size = 0
            max_size_bytes = self.video_max_size_mb * 1024 * 1024

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix='.mp4',
                dir=self.cache_dir
            ) as tmp_file:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        total_size += len(chunk)
                        if total_size > max_size_bytes:
                            logger.warning(f"[MMM] 视频下载超过大小限制: {total_size / (1024*1024):.2f}MB")
                            os.remove(tmp_file.name)
                            return None
                        tmp_file.write(chunk)

                logger.info(f"[MMM] 视频下载完成: {tmp_file.name}, 大小: {total_size / (1024*1024):.2f}MB")
                return tmp_file.name

        except Exception as e:
            logger.error(f"[MMM] 下载视频文件异常 {url}: {e}")
            return None

    def get_help_text(self, **kwargs):
        """获取帮助文本"""
        help_text = "MMM美图视频插件\n\n"
        help_text += "图片触发关键词：\n"
        for image_type, keywords in self.triggers.items():
            help_text += f"  {image_type}: {', '.join(keywords)}\n"
        help_text += "\n视频触发关键词：\n"
        for video_type, keywords in self.video_triggers.items():
            help_text += f"  {video_type}: {', '.join(keywords)}\n"
        help_text += "\n在消息中包含任意关键词即可触发"
        return help_text
