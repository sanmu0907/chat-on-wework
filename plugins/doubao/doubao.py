# encoding:utf-8

import json
import os
import aiohttp
import asyncio
from datetime import datetime, date
from pathlib import Path
import plugins
from bridge.context import ContextType
from bridge.reply import Reply, ReplyType
from common.log import logger
from plugins import *


@plugins.register(
    name="Doubao",
    desire_priority=100,
    hidden=False,
    desc="字节跳动豆包AI助手，支持对话和图片生成",
    version="1.0.0",
    author="adapted for chatgpt-on-wechat",
)
class Doubao(Plugin):
    def __init__(self):
        super().__init__()
        try:
            curdir = os.path.dirname(__file__)
            config_path = os.path.join(curdir, "config.json")

            # 加载配置
            if not os.path.exists(config_path):
                logger.warn(f"[Doubao] 配置文件不存在: {config_path}")
                raise Exception("配置文件不存在，请参考config.json.template创建config.json")

            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # 基础配置
            self.conversation_id = config.get("conversation_id", "")
            self.cookie = config.get("cookie", "")

            # 支持新旧两种配置格式
            commands_config = config.get("commands", ["豆包", "豆", "doubao", "db"])
            if isinstance(commands_config, dict):
                # 新格式：字典，按功能分类
                self.commands = commands_config
                self.all_commands = []
                for cmd_list in commands_config.values():
                    self.all_commands.extend(cmd_list)
            else:
                # 旧格式：列表，兼容性处理
                self.commands = {"chat": commands_config}
                self.all_commands = commands_config

            # 功能开关
            self.private_chat = config.get("private_chat", True)
            self.group_chat = config.get("group_chat", True)
            self.daily_limit = config.get("daily_limit", 0)  # 0表示无限制

            # 新功能开关
            self.enable_super_mode = config.get("enable_super_mode", True)
            self.enable_music = config.get("enable_music", False)
            self.enable_podcast = config.get("enable_podcast", False)

            # 音乐生成默认参数
            self.music_default_style = config.get("music_default_style", "民谣")
            self.music_default_mood = config.get("music_default_mood", "快乐")
            self.music_default_voice = config.get("music_default_voice", "女声")

            # 验证必需配置
            if not self.conversation_id or not self.cookie:
                raise Exception("conversation_id 和 cookie 为必需配置项")

            # 创建缓存目录
            self.cache_dir = Path(curdir) / "cache"
            self.cache_dir.mkdir(parents=True, exist_ok=True)

            # 固定设备ID（从真实curl请求中提取，避免频率限制）
            self.device_id = "1176928240801724"
            self.web_id = "7564426004640761407"
            self.aid = "582478"  # 应用ID，必须和浏览器一致
            self.pc_version = "1.85.7"  # PC客户端版本

            # 用户使用次数统计
            self.user_usage = {}  # {user_id: {date: count}}

            # 用户模式状态 (新增功能：模式切换)
            self.user_mode = {}  # {user_id: "chat"|"super"|"music"|"podcast"}

            # 防限流机制
            self.last_request_time = 0  # 上次请求时间戳
            self.min_request_interval = 3.0  # 最小请求间隔（秒）
            self.retry_delay = 5.0  # 限流重试延迟（秒）
            self.max_retry = 2  # 最大重试次数

            # 注册事件处理器
            self.handlers[Event.ON_HANDLE_CONTEXT] = self.on_handle_context
            logger.info(f"[Doubao] 初始化成功")
            logger.info(f"[Doubao] 对话触发词: {self.commands.get('chat', [])}")
            logger.info(f"[Doubao] 模式切换: 发送 '豆包 切换到超能模式' 启用深度推理")
            logger.info(f"[Doubao] 防限流: 最小间隔{self.min_request_interval}秒, 重试延迟{self.retry_delay}秒")
            if self.enable_super_mode:
                logger.info(f"[Doubao] 超能模式: 支持模式切换 + 单次触发词 {self.commands.get('super', [])}")
            if self.enable_music:
                logger.info(f"[Doubao] 音乐生成触发词: {self.commands.get('music', [])}")
            if self.enable_podcast:
                logger.info(f"[Doubao] 播客生成触发词: {self.commands.get('podcast', [])}")

        except Exception as e:
            logger.error(f"[Doubao] 初始化失败: {e}")
            raise e

    def on_handle_context(self, e_context: EventContext):
        """处理消息上下文"""
        try:
            context_type = e_context["context"].type
            origin_ctype = e_context["context"].get("origin_ctype")

            # 检测是否是引用图片的场景
            is_quote_image = False
            image_path = None
            original_text_content = None

            if context_type == ContextType.IMAGE and origin_ctype == ContextType.TEXT:
                # 这是引用图片的场景：
                # - 原始消息是TEXT（包含"「用户：[图片]」\n豆包 xxx"）
                # - chat_channel转换为IMAGE类型
                # - context.content是图片路径
                image_path = e_context["context"].content
                # 从msg中获取原始文本
                msg = e_context["context"].kwargs.get("msg")
                if msg and hasattr(msg, "content"):
                    original_text_content = msg.content
                    logger.info(f"[Doubao] 检测到引用图片场景，图片路径: {image_path}, 原始文本: {original_text_content[:50] if original_text_content else 'None'}...")
                    is_quote_image = True

            # 只处理文本消息或引用图片消息
            if context_type != ContextType.TEXT and not is_quote_image:
                return

            # 获取content
            if is_quote_image:
                content = original_text_content if original_text_content else ""
            else:
                content = e_context["context"].content.strip()

            is_group = e_context["context"].get("isgroup", False)
            user_id = e_context["context"].get("receiver", "")

            # 检查群聊/私聊开关
            if is_group and not self.group_chat:
                return
            if not is_group and not self.private_chat:
                return

            # 检查是否触发命令
            is_triggered, feature_type, clean_content, quote_info = self._is_command_triggered(content)
            if not is_triggered:
                return

            logger.info(f"[Doubao] 触发命令，功能类型: {feature_type}, 内容: {clean_content[:50]}, 是否引用: {quote_info is not None}")

            # ===== 新增：超能模式切换功能 =====
            # 检测模式切换指令（只支持超能模式切换）
            import re
            mode_switch_pattern = r'^(切换到?|查看|当前)?(普通|超能)?模式?$'
            mode_match = re.match(mode_switch_pattern, clean_content.strip())

            if mode_match or clean_content.strip() in ["当前模式", "查看模式", "模式"]:
                # 查看当前模式
                if clean_content.strip() in ["当前模式", "查看模式", "模式"] or (mode_match.group(1) in ["查看", "当前"] if mode_match.group(1) else False):
                    current_mode = self.user_mode.get(user_id, "chat")
                    mode_names = {
                        "chat": "普通模式（可对话、生成音乐、播客、图片等）",
                        "super": "超能模式（深度推理+多轮搜索）"
                    }
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = f"📍 当前模式：{mode_names.get(current_mode, '普通模式')}"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return

                # 切换模式
                if mode_match and mode_match.group(2):
                    target_mode_name = mode_match.group(2)
                    mode_mapping = {
                        "普通": "chat",
                        "超能": "super"
                    }
                    target_mode = mode_mapping.get(target_mode_name)

                    if target_mode:
                        # 检查超能模式是否启用
                        if target_mode == "super" and not self.enable_super_mode:
                            reply = Reply()
                            reply.type = ReplyType.TEXT
                            reply.content = "超能模式未启用，请在配置文件中设置enable_super_mode=true"
                            e_context["reply"] = reply
                            e_context.action = EventAction.BREAK_PASS
                            return

                        # 切换模式
                        self.user_mode[user_id] = target_mode
                        mode_desc = {
                            "chat": "普通模式",
                            "super": "超能模式（深度推理+多轮搜索）"
                        }
                        tips = {
                            "chat": "现在可以正常对话，也可以使用：\n• 音乐 [描述] - 生成音乐\n• 播客 [链接/内容] - 生成播客",
                            "super": "后续对话将使用深度推理和多轮搜索"
                        }
                        reply = Reply()
                        reply.type = ReplyType.TEXT
                        reply.content = f"✅ 已切换到{mode_desc[target_mode]}\n\n{tips[target_mode]}"
                        logger.info(f"[Doubao] 用户 {user_id} 切换到 {target_mode} 模式")
                        e_context["reply"] = reply
                        e_context.action = EventAction.BREAK_PASS
                        return

            # 如果用户处于超能模式，且当前不是music/podcast类型，则覆盖为super
            if user_id in self.user_mode and self.user_mode[user_id] == "super":
                # 只有在纯对话时才使用超能模式，音乐/播客仍使用原始功能
                if feature_type == "chat":
                    feature_type = "super"
                    logger.info(f"[Doubao] 用户处于超能模式，普通对话将使用深度推理")
            # ===== 超能模式切换功能结束 =====

            # 检查功能是否启用
            if feature_type == "super" and not self.enable_super_mode:
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = "超能模式未启用，请在配置文件中设置enable_super_mode=true"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif feature_type == "music" and not self.enable_music:
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = "音乐生成功能未启用，请在配置文件中设置enable_music=true"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return
            elif feature_type == "podcast" and not self.enable_podcast:
                reply = Reply()
                reply.type = ReplyType.TEXT
                reply.content = "播客生成功能未启用，请在配置文件中设置enable_podcast=true"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS
                return

            # 检查每日限制
            if self.daily_limit > 0:
                if not self._check_user_limit(user_id):
                    reply = Reply()
                    reply.type = ReplyType.TEXT
                    reply.content = f"您今日的对话次数已达上限({self.daily_limit}次)，请明天再试"
                    e_context["reply"] = reply
                    e_context.action = EventAction.BREAK_PASS
                    return

            # 调用豆包API
            try:
                # 根据功能类型调用不同的方法
                if feature_type == "music":
                    # 音乐生成
                    logger.info(f"[Doubao] 准备生成音乐: {clean_content[:100]}")
                    response_text, media_urls = asyncio.run(self._generate_music(clean_content))
                elif feature_type == "podcast":
                    # 播客生成
                    logger.info(f"[Doubao] 准备生成播客: {clean_content[:100]}")
                    response_text, media_urls = asyncio.run(self._generate_podcast(clean_content))
                else:
                    # 普通对话或超能模式
                    use_super = (feature_type == "super")
                    logger.info(f"[Doubao] 准备对话，超能模式: {use_super}，引用消息: {quote_info is not None}，引用图片: {is_quote_image}")
                    response_text, media_urls = asyncio.run(
                        self._chat_with_doubao(
                            clean_content,
                            use_super_mode=use_super,
                            quote_info=quote_info,
                            image_path=image_path if is_quote_image else None
                        )
                    )

                # media_urls可能是图片或音频
                image_urls = media_urls if media_urls else []

                # 构造回复
                reply = Reply()

                # 如果有图片，发送所有图片
                if image_urls:
                    logger.info(f"[Doubao] 获取到{len(image_urls)}张图片")

                    # 发送第一张图片
                    reply.type = ReplyType.IMAGE_URL
                    reply.content = image_urls[0]
                    logger.info(f"[Doubao] 发送第1张图片: {image_urls[0][:80]}")

                    # 如果有多张图片，通过channel依次发送其他图片
                    if len(image_urls) > 1:
                        # 获取当前channel实例
                        try:
                            # 从context获取channel实例
                            msg = e_context["context"].kwargs.get("msg")
                            if msg and hasattr(msg, "channel"):
                                active_channel = msg.channel
                            else:
                                # 从全局获取
                                from channel.channel_factory import create_channel
                                from config import conf
                                channel_type = conf().get("channel_type", "wework")
                                active_channel = create_channel(channel_type)

                            # 发送剩余图片
                            for idx in range(1, len(image_urls)):
                                additional_reply = Reply(ReplyType.IMAGE_URL, image_urls[idx])
                                logger.info(f"[Doubao] 发送第{idx+1}张图片: {image_urls[idx][:80]}")
                                # 使用当前context发送
                                try:
                                    active_channel.send(additional_reply, e_context["context"])
                                except Exception as send_err:
                                    logger.error(f"[Doubao] 发送第{idx+1}张图片失败: {send_err}")
                        except Exception as ch_err:
                            logger.error(f"[Doubao] 获取channel失败，无法发送额外图片: {ch_err}")

                    # 如果有文本说明，添加到日志
                    if response_text:
                        logger.info(f"[Doubao] 图片说明: {response_text}")
                else:
                    # 没有图片，发送文本
                    reply.type = ReplyType.TEXT
                    reply.content = response_text

                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

            except Exception as api_err:
                logger.error(f"[Doubao] API调用失败: {api_err}")
                reply = Reply()
                reply.type = ReplyType.ERROR
                reply.content = f"豆包API调用失败: {str(api_err)}"
                e_context["reply"] = reply
                e_context.action = EventAction.BREAK_PASS

        except Exception as e:
            logger.error(f"[Doubao] 处理消息失败: {e}")

    def _is_command_triggered(self, content: str) -> tuple:
        """
        检查消息是否以命令列表中的命令开头，支持引用消息

        Returns:
            (是否触发命令, 功能类型, 去除命令前缀后的内容, 引用消息字典或None)
            功能类型: "chat", "super", "music", "podcast"
            引用消息字典: {"quoted_content": str, "user_instruction": str} 或 None
        """
        if not content:
            return False, "chat", content, None

        # 检测是否是引用消息格式
        # 格式: "「用户名：原文内容」\n- - - - - - - - - - - - - - -\n豆包"
        import re
        quote_pattern = r'^「([^：]+)：(.+?)」\s*\n[-\s]+\n(.*)$'
        quote_match = re.match(quote_pattern, content, re.DOTALL)

        if quote_match:
            # 提取被引用用户名和原文
            quoted_user = quote_match.group(1).strip()
            quoted_content = quote_match.group(2).strip()
            # 提取引用后的文本
            after_quote = quote_match.group(3).strip()

            logger.info(f"[Doubao] 检测到引用消息，来自: {quoted_user}，内容: {quoted_content[:50]}...")

            # 检查引用后的文本是否触发命令（优先检查特定功能）
            # 优先级: music > podcast > super > chat
            for feature_type in ["music", "podcast", "super", "chat"]:
                if feature_type not in self.commands:
                    continue
                for cmd in self.commands[feature_type]:
                    cmd_lower = cmd.lower()
                    if after_quote.lower().startswith(cmd_lower):
                        # 去除命令前缀
                        user_instruction = after_quote[len(cmd):].strip()

                        # 构建引用消息结构
                        quote_info = {
                            "quoted_user": quoted_user,
                            "quoted_content": quoted_content,
                            "user_instruction": user_instruction
                        }

                        # 如果命令后没有额外内容，使用引用的内容作为prompt
                        if not user_instruction:
                            clean_content = quoted_content
                            logger.info(f"[Doubao] 使用引用内容作为prompt: {clean_content[:50]}...")
                        else:
                            # 如果有用户指令，组合引用内容和指令
                            clean_content = f"{quoted_content}\n\n{user_instruction}"
                            logger.info(f"[Doubao] 引用内容+用户指令: {clean_content[:50]}...")

                        return True, feature_type, clean_content, quote_info

        # 常规命令检测
        # 步骤1: 先去除通用chat前缀（如"豆包"）
        content_lower = content.lower()
        stripped_content = content
        chat_prefix_removed = False

        for cmd in self.commands.get("chat", []):
            cmd_lower = cmd.lower()
            if content_lower.startswith(cmd_lower):
                # 去除chat前缀
                stripped_content = content[len(cmd):].strip()
                chat_prefix_removed = True
                logger.debug(f"[Doubao] 去除chat前缀 '{cmd}'，剩余: {stripped_content}")
                break

        # 步骤2: 检查去除前缀后的内容是否包含特定功能触发词
        # 优先级: music > podcast > super
        # 注意: 按触发词长度降序排列，优先匹配更长的触发词（避免"音乐"误匹配"音乐生成"）
        stripped_lower = stripped_content.lower()
        for feature_type in ["music", "podcast", "super"]:
            if feature_type not in self.commands:
                continue
            # 按长度降序排序触发词
            sorted_cmds = sorted(self.commands[feature_type], key=len, reverse=True)
            for cmd in sorted_cmds:
                cmd_lower = cmd.lower()
                if stripped_lower.startswith(cmd_lower):
                    # 找到特定功能触发词
                    clean_content = stripped_content[len(cmd):].strip()
                    logger.debug(f"[Doubao] 在去除前缀后发现 {feature_type} 触发词 '{cmd}'")
                    return True, feature_type, clean_content, None

        # 步骤3: 如果去除了chat前缀但没有找到特定功能，默认为chat
        if chat_prefix_removed:
            return True, "chat", stripped_content, None

        # 步骤4: 没有匹配任何触发词
        return False, "chat", content, None

    def _check_user_limit(self, user_id: str) -> bool:
        """检查用户是否超过每日限制"""
        if self.daily_limit <= 0:
            return True

        today = str(date.today())

        if user_id not in self.user_usage:
            self.user_usage[user_id] = {}

        if today not in self.user_usage[user_id]:
            self.user_usage[user_id][today] = 0

        if self.user_usage[user_id][today] >= self.daily_limit:
            return False

        self.user_usage[user_id][today] += 1
        return True

    async def _chat_with_doubao(self, prompt: str, use_super_mode: bool = False, quote_info: dict = None, image_path: str = None) -> tuple:
        """
        与豆包AI对话（带防限流和重试机制）

        Args:
            prompt: 用户输入的内容
            use_super_mode: 是否启用超能模式（深度思考）
            quote_info: 引用消息信息，格式: {"quoted_user": str, "quoted_content": str, "user_instruction": str}
            image_path: 引用的图片路径（可选）

        Returns:
            (回复文本, 图片URL列表)
        """
        import uuid
        import time
        import asyncio

        # 防限流：检查请求间隔
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.min_request_interval:
            wait_time = self.min_request_interval - time_since_last
            logger.info(f"[Doubao] 防限流：等待 {wait_time:.1f}秒")
            await asyncio.sleep(wait_time)

        # 重试逻辑
        for retry_count in range(self.max_retry + 1):
            try:
                # 更新最后请求时间
                self.last_request_time = time.time()

                # 调用实际的请求方法
                return await self._do_chat_request(prompt, use_super_mode, quote_info, image_path)

            except Exception as e:
                error_msg = str(e)

                # 检查是否为限流错误
                if "rate limited" in error_msg or "710022004" in error_msg:
                    if retry_count < self.max_retry:
                        logger.warning(f"[Doubao] 触发限流，{self.retry_delay}秒后重试 ({retry_count + 1}/{self.max_retry})")
                        await asyncio.sleep(self.retry_delay)
                        continue
                    else:
                        logger.error(f"[Doubao] 达到最大重试次数，限流无法解除")
                        return "豆包服务繁忙（触发限流），请稍后再试", []
                else:
                    # 非限流错误，直接抛出
                    raise e

        return "请求失败，请稍后再试", []

    async def _do_chat_request(self, prompt: str, use_super_mode: bool = False, quote_info: dict = None, image_path: str = None) -> tuple:
        """
        实际执行与豆包AI对话的请求（内部方法）

        Args:
            prompt: 用户输入的内容
            use_super_mode: 是否启用超能模式
            quote_info: 引用消息信息
            image_path: 引用的图片路径（可选）

        Returns:
            (回复文本, 图片URL列表)
        """
        import uuid
        import time
        import re

        # 如果有引用图片，从豆包对话历史中找到对应的消息
        ref_image_message_id = None
        ref_image_urls = []

        if image_path and quote_info:
            logger.info(f"[Doubao] 检测到图片引用，尝试从对话历史匹配引用的图片")
            try:
                # 从缓存文件名提取时间戳 (格式: userid_timestamp.jpg)
                # 例如: 1688857885797559_1767662129.jpg
                filename = image_path.split("\\")[-1].split("/")[-1]
                timestamp_match = re.search(r'_(\d+)\.jpg$', filename)

                if timestamp_match:
                    image_timestamp = int(timestamp_match.group(1))
                    logger.info(f"[Doubao] 从缓存文件名提取时间戳: {image_timestamp}")

                    # 从历史中查找该时间戳附近的消息
                    message_info = await self._find_image_message_by_timestamp(image_timestamp)
                    if message_info:
                        ref_image_message_id = message_info["message_id"]
                        ref_image_urls = message_info["image_urls"]
                        logger.info(f"[Doubao] 找到引用图片的消息ID: {ref_image_message_id}, 图片数: {len(ref_image_urls)}")
                        # 将message_id添加到quote_info中，供后续使用
                        quote_info["ref_message_id"] = ref_image_message_id
                        quote_info["ref_image_urls"] = ref_image_urls
                    else:
                        # 历史中找不到，说明是外部图片
                        # 尝试上传到图床获取公网URL，然后尝试传给豆包
                        logger.info(f"[Doubao] 未在历史中找到图片，尝试上传到图床获取URL")

                        try:
                            from common.superbed_uploader import get_superbed_uploader
                            uploader = get_superbed_uploader()
                            upload_result = uploader.upload_file(image_path)

                            if upload_result.get("success"):
                                external_url = upload_result.get("link")
                                logger.info(f"[Doubao] 图片上传成功: {external_url}")
                                # 将外部URL存储，尝试传给豆包
                                quote_info["external_image_url"] = external_url
                                quote_info["is_external_image"] = True
                            else:
                                logger.warning(f"[Doubao] 图片上传失败: {upload_result.get('error')}")
                                # 降级到视觉模型识别
                                logger.info(f"[Doubao] 降级到视觉模型识别")
                                image_description = await self._recognize_image_for_generation(image_path)
                                if image_description:
                                    logger.info(f"[Doubao] 图片识别成功，描述长度: {len(image_description)}")
                                    prompt = f"参考图片描述：{image_description}\n\n{prompt}"
                                    quote_info["is_external_image"] = True
                        except Exception as upload_err:
                            logger.error(f"[Doubao] 上传图片异常: {upload_err}")
                            # 降级到视觉模型识别
                            logger.info(f"[Doubao] 降级到视觉模型识别")
                            image_description = await self._recognize_image_for_generation(image_path)
                            if image_description:
                                logger.info(f"[Doubao] 图片识别成功，描述长度: {len(image_description)}")
                                prompt = f"参考图片描述：{image_description}\n\n{prompt}"
                                quote_info["is_external_image"] = True
                else:
                    logger.warning(f"[Doubao] 无法从文件名提取时间戳: {filename}")

            except Exception as e:
                logger.error(f"[Doubao] 获取对话历史图片失败: {e}")

        # 不使用base64，使用消息引用方式
        image_base64 = None

        # 超能模式使用不同的API端点
        if use_super_mode:
            base_url = "https://www.doubao.com/samantha/chat/completion"
        else:
            base_url = "https://www.doubao.com/chat/completion"

        # 构建URL参数（参考实际curl命令）
        url_params = {
            "aid": self.aid,
            "device_id": self.device_id,
            "device_platform": "web",
            "language": "zh",
            "pc_version": self.pc_version,
            "pkg_type": "release_version",
            "real_aid": self.aid,
            "region": "CN",
            "samantha_web": "1",
            "sys_region": "CN",
            "tea_uuid": self.device_id,  # tea_uuid应该等于device_id
            "use-olympus-account": "1",
            "version_code": "20800",
            "web_id": self.web_id,
            # 添加额外的静态参数（从curl命令中提取）
            "chromium_version": "135.0.7049.72",
            "client_platform": "pc_client",
            "runtime": "web",
            "runtime_version": "2.51.1",  # ⚠️ 关键：这个必须是2.51.1，不是pc_version
            # 添加指纹和标签ID（从最新curl提取）
            "fp": "verify_mjjb8r0e_GKFjCZdR_tlFL_4gPj_AaQX_5TnXwESL36YJ",
            "web_tab_id": "5db14d17-a217-43e3-a418-c14a55dc7aa9",
            # 动态防爬参数（从2025-12-29 17:07最新curl提取，可能会快速过期）
            "msToken": "PloAzJxvWIp-5D02X3t_bFKRRwsGhfAy71BF4Qc_3CVhWoa0f1ATecaQesmDYQdUq1tsFvZdSkayn8dfuCzs0WsyV2AbfiqrT9vbvplyiZl_8QU6DsWK7gw_49lmEncKTPjUK-NpvwFasKo69f4qPcE8aWeUcSw_sj7UIAsjZA03",
            "a_bogus": "Ef0fgqtwOpQjKdMS8KDEH-V1-X2/NP8ysFi/bErRS1C2O7MOE2F0Kw4ejxNHzXLEEumcFqrHsncKcfnczu-XAMHpFmZDSzzWxGQcIU0LhqZvGakZ936xCDSEqksS8SGOTC5tNPE16z0E1oOvD19iWeF9SCz7Bum0/ZabDrWlCx2QgGkYIIA1CBZw",
        }

        # 构建请求头
        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "agw-js-conv": "str, str",
            "content-type": "application/json",
            "last-event-id": "undefined",
            "origin": "https://www.doubao.com",
            "priority": "u=1, i",
            "referer": f"https://www.doubao.com/chat/{self.conversation_id}",
            "sec-ch-ua": '"Chromium";v="135", "Not-A.Brand";v="8"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": f"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36 SamanthaDoubao/{self.pc_version}",
            "x-flow-trace": "04-00181f2a2454b8b5000f6d70b97cdd8a-001528c8b509a24b-01",  # 追踪头（可能动态）
            "cookie": self.cookie,
        }

        # 生成UUID
        local_message_id = str(uuid.uuid4())
        block_id = str(uuid.uuid4())
        unique_key = str(uuid.uuid4())
        client_tool_key = str(uuid.uuid4())

        # 构建引用消息的references数组
        references = []

        if quote_info:
            # 如果有引用消息，添加到references
            reference = {
                "type": "quote",  # 引用类型
                "content": quote_info["quoted_content"],
                "user": quote_info.get("quoted_user", "用户"),
            }

            # 如果找到了引用图片的原始消息ID，添加到引用中
            if "ref_message_id" in quote_info:
                reference["message_id"] = quote_info["ref_message_id"]
                logger.info(f"[Doubao] 在references中添加message_id: {quote_info['ref_message_id']}")

                # 同时添加图片URL信息（如果有）
                if "ref_image_urls" in quote_info and quote_info["ref_image_urls"]:
                    reference["ref_image_url"] = quote_info["ref_image_urls"][0]
                    logger.info(f"[Doubao] 在references中添加ref_image_url: {quote_info['ref_image_urls'][0][:100]}")

            # 如果是外部图片（已上传到图床），尝试添加URL
            elif "external_image_url" in quote_info:
                external_url = quote_info["external_image_url"]
                reference["ref_image_url"] = external_url
                logger.info(f"[Doubao] 在references中添加外部图片URL: {external_url}")

            references.append(reference)
            logger.info(f"[Doubao] 添加引用消息到请求: 来自 {quote_info.get('quoted_user', '用户')}")


        # 超能模式使用不同的API格式（content_type: 2535 + skill_id: 138）
        if use_super_mode:
            # 构建超能模式消息内容
            message_content = {
                "clarify": "",
                "text": prompt,
                "language": "zh",
                "task_type": 0,
                "client_tool_key": client_tool_key
            }

            payload = {
                "messages": [
                    {
                        "content": json.dumps(message_content),
                        "content_type": 2535,  # 超能模式内容类型
                        "references": references  # 添加引用消息（包含message_id和ref_image_url）
                    }
                ],
                "completion_option": {
                    "is_regen": False,
                    "with_suggest": False,
                    "need_create_conversation": False,
                    "launch_stage": 1,
                    "is_replace": False,  # ✅ 超能模式必须为False
                    "is_delete": False,
                    "is_ai_playground": False,
                    "message_from": 0,
                    "action_bar_skill_id": 138,  # 超能模式技能ID
                    "use_deep_think": False,
                    "use_auto_cot": False,
                    "resend_for_regen": False,
                    "enable_commerce_credit": False,
                    "event_id": "0"
                },
                "evaluate_option": {
                    "web_ab_params": ""
                },
                "section_id": "",
                "conversation_id": self.conversation_id
            }
        else:
            # 普通对话使用旧格式（content_block）
            # 构建content_block数组
            content_blocks = []

            # 如果有引用消息，先添加引用块
            if quote_info:
                quote_block_content = {
                    "quote_block": {
                        "text": quote_info["quoted_content"],
                        "user": quote_info.get("quoted_user", "用户")
                    }
                }

                # 如果找到了引用图片的原始消息ID，添加到引用块中
                if "ref_message_id" in quote_info:
                    quote_block_content["quote_block"]["message_id"] = quote_info["ref_message_id"]
                    logger.info(f"[Doubao] 在引用块中添加message_id: {quote_info['ref_message_id']}")

                    # 同时添加图片URL信息（如果有）
                    if "ref_image_urls" in quote_info and quote_info["ref_image_urls"]:
                        # 只取第一张图片作为引用（通常用户引用的是单张图片）
                        quote_block_content["quote_block"]["ref_image_url"] = quote_info["ref_image_urls"][0]
                        logger.info(f"[Doubao] 在引用块中添加ref_image_url: {quote_info['ref_image_urls'][0][:100]}")

                # 如果是外部图片（已上传到图床），尝试添加URL
                elif "external_image_url" in quote_info:
                    external_url = quote_info["external_image_url"]
                    quote_block_content["quote_block"]["ref_image_url"] = external_url
                    logger.info(f"[Doubao] 在引用块中添加外部图片URL: {external_url}")

                quote_block = {
                    "block_type": 10001,  # 引用消息块类型
                    "content": quote_block_content,
                    "block_id": str(uuid.uuid4()),
                    "parent_id": "",
                    "meta_info": [],
                    "append_fields": []
                }
                content_blocks.append(quote_block)
                logger.info(f"[Doubao] 添加引用块到content_block")


            # 注意：图片不使用image_block，而是在引用块中携带

            # 添加文本块
            text_block = {
                "block_type": 10000,
                "content": {
                    "text_block": {
                        "text": prompt,
                        "icon_url": "",
                        "icon_url_dark": "",
                        "summary": ""
                    },
                    "pc_event_block": ""
                },
                "block_id": block_id,
                "parent_id": "",
                "meta_info": [],
                "append_fields": []
            }
            content_blocks.append(text_block)

            # 构建messages对象
            message_obj = {
                "local_message_id": local_message_id,
                "content_block": content_blocks,
                "message_status": 0
            }

            payload = {
                "client_meta": {
                    "conversation_id": self.conversation_id,
                    "bot_id": "7338286299411103781",
                    "last_section_id": "",
                    "last_message_index": 0
                },
                "messages": [message_obj],
                "option": {
                    "send_message_scene": "",
                    "create_time_ms": int(time.time() * 1000),
                    "collect_id": "",
                    "is_audio": False,
                    "answer_with_suggest": False,
                    "tts_switch": False,
                    "need_deep_think": 0,
                    "click_clear_context": False,
                    "from_suggest": False,
                    "is_regen": False,
                    "is_replace": False,
                    "disable_sse_cache": False,
                    "select_text_action": "",
                    "resend_for_regen": False,
                    "scene_type": 0,
                    "unique_key": unique_key,
                    "start_seq": 0,
                    "need_create_conversation": False,
                    "regen_query_id": [],
                    "edit_query_id": [],
                    "regen_instruction": "",
                    "no_replace_for_regen": False,
                    "message_from": 0,
                    "shared_app_name": "",
                    "sse_recv_event_options": {
                        "support_chunk_delta": True
                    },
                    "is_ai_playground": False
                },
                "ext": {
                    "use_deep_think": "0",
                    "commerce_credit_config_enable": "0",
                    "sub_conv_firstmet_type": "0"
                }
            }

        # 发送请求
        try:
            # 详细调试日志：输出完整请求信息
            logger.info(f"[Doubao] 请求URL: {base_url}")
            logger.info(f"[Doubao] URL参数: {url_params}")
            logger.debug(f"[Doubao] 请求头(不含cookie): {dict((k, v) for k, v in headers.items() if k.lower() != 'cookie')}")
            logger.info(f"[Doubao] 请求体: {json.dumps(payload, ensure_ascii=False)[:1000]}")

            async with aiohttp.ClientSession() as session:
                async with session.post(
                    base_url,
                    params=url_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"API请求失败: {response.status}, {error_text[:200]}")

                    # 逐行读取SSE流式响应，等待完整响应
                    sse_lines = []
                    buffer = b""

                    async for chunk in response.content.iter_any():
                        buffer += chunk
                        # 按行分割
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            line_text = line_bytes.decode('utf-8', errors='ignore').strip()
                            if line_text:
                                sse_lines.append(line_text)
                                # 检查是否收到结束标记 event_type:2003
                                if '"event_type":2003' in line_text:
                                    logger.debug(f"[Doubao] 收到完成标记，停止读取")
                                    break
                        else:
                            continue
                        break

                    content = '\n'.join(sse_lines)

                    # 记录原始响应（前3000字符用于调试）
                    logger.debug(f"[Doubao] 原始响应: {content[:3000]}")

                    # 解析SSE格式响应
                    response_text = ""
                    image_urls = []
                    async_task_id = None

                    # 过滤掉中间状态消息
                    ignore_texts = ["任务执行中", "正在处理", "生成中"]

                    try:
                        lines = content.strip().split('\n')
                        logger.debug(f"[Doubao] 收到{len(lines)}行SSE数据")

                        # 检测限流错误
                        for line in lines:
                            if '"error_code":710022004' in line or '"error_msg":"rate limited"' in line:
                                logger.error(f"[Doubao] 检测到限流错误: {line[:200]}")
                                raise Exception("rate limited")
                            # 检测STREAM_ERROR事件
                            if 'event: STREAM_ERROR' in line:
                                logger.warning(f"[Doubao] 检测到流错误事件")

                        for line in lines:
                            line = line.strip()
                            if not line or line.startswith(':'):
                                continue

                            # 解析 "data: {json}" 格式
                            if line.startswith('data: '):
                                json_str = line[6:]
                                try:
                                    data = json.loads(json_str)
                                    logger.debug(f"[Doubao] 解析到data: {str(data)[:200]}")

                                    # 检查根层级的图片生成任务 (patch_op with block_type: 2074)
                                    if "patch_op" in data and "message_id" in data:
                                        for patch in data["patch_op"]:
                                            if "patch_value" in patch and "content_block" in patch["patch_value"]:
                                                for block in patch["patch_value"]["content_block"]:
                                                    block_type = block.get("block_type")

                                                    # block_type 2074: 图片生成任务
                                                    if block_type == 2074:
                                                        async_task_id = data["message_id"]
                                                        logger.info(f"[Doubao] 检测到图片生成任务，message_id: {async_task_id}")

                                                        # 打印完整的block结构以便调试
                                                        logger.debug(f"[Doubao] block_2074完整结构: {json.dumps(block, ensure_ascii=False)[:1000]}")

                                                        # 直接从creation_block中提取图片URL
                                                        if "content" in block and "creation_block" in block["content"]:
                                                            creation = block["content"]["creation_block"]
                                                            logger.debug(f"[Doubao] creation_block内容: {json.dumps(creation, ensure_ascii=False)[:1000]}")

                                                            # 从creations数组中提取（新版API格式）
                                                            if "creations" in creation:
                                                                logger.info(f"[Doubao] 找到creations数组，共{len(creation['creations'])}个创作")
                                                                for idx, item in enumerate(creation["creations"]):
                                                                    if "image" in item:
                                                                        img = item["image"]
                                                                        # 优先使用原图
                                                                        if "image_ori" in img and "url" in img["image_ori"]:
                                                                            url = img["image_ori"]["url"]
                                                                            image_urls.append(url)
                                                                            logger.info(f"[Doubao] 从creations[{idx}].image_ori提取图片: {url[:100]}")
                                                                        # 备选缩略图
                                                                        elif "image_thumb" in img and "url" in img["image_thumb"]:
                                                                            url = img["image_thumb"]["url"]
                                                                            image_urls.append(url)
                                                                            logger.info(f"[Doubao] 从creations[{idx}].image_thumb提取图片: {url[:100]}")

                                                            # 从result中提取（旧版格式）
                                                            elif "result" in creation:
                                                                result = creation["result"]
                                                                if "image_urls" in result:
                                                                    urls = result["image_urls"]
                                                                    image_urls.extend(urls)
                                                                    logger.info(f"[Doubao] 从result.image_urls提取到{len(urls)}张图片")
                                                                elif "images" in result:
                                                                    for img in result["images"]:
                                                                        if "url" in img:
                                                                            image_urls.append(img["url"])

                                                            # 从artifacts中提取（备选）
                                                            elif "artifacts" in creation:
                                                                for artifact in creation["artifacts"]:
                                                                    if artifact.get("type") == "image" and "url" in artifact:
                                                                        image_urls.append(artifact["url"])
                                                                        logger.info(f"[Doubao] 从artifacts提取图片")

                                                    # block_type 10000: 文本块，也提取文本
                                                    elif block_type == 10000 and "content" in block:
                                                        if "text_block" in block["content"]:
                                                            text = block["content"]["text_block"].get("text", "")
                                                            if text and not any(ignore in text for ignore in ignore_texts):
                                                                response_text += text
                                                                logger.debug(f"[Doubao] 从patch_op提取文本: {text[:50]}")

                                    # 检查是否是错误事件 (event_type 2005)
                                    if data.get("event_type") == 2005:
                                        try:
                                            event_data = json.loads(data["event_data"])
                                            error_msg = event_data.get("error_detail", {}).get("message", "API返回错误")
                                            logger.error(f"[Doubao] API错误: {error_msg}")
                                            response_text = error_msg
                                            # 遇到错误，直接返回
                                            logger.info(f"[Doubao] 解析结果: 文本长度={len(response_text)}, 图片数={len(image_urls)}")
                                            return response_text, image_urls
                                        except Exception as e:
                                            logger.error(f"[Doubao] 解析错误消息失败: {e}")
                                            pass

                                    # 提取event_data中的内容
                                    if "event_data" in data:
                                        try:
                                            event_data = json.loads(data["event_data"])
                                            logger.debug(f"[Doubao] event_data: {str(event_data)[:200]}")

                                            # 检查异步任务 (旧版格式)
                                            if "fin_reason" in event_data:
                                                fin_reason = event_data.get("fin_reason", {})
                                                if "async_task" in fin_reason and "id" in fin_reason["async_task"]:
                                                    async_task_id = fin_reason["async_task"]["id"]
                                                    logger.info(f"[Doubao] 检测到异步任务: {async_task_id}")

                                            # 提取message中的content
                                            if "message" in event_data:
                                                msg = event_data["message"]

                                                # 提取文本内容
                                                if "content" in msg:
                                                    content_text = msg["content"]
                                                    logger.debug(f"[Doubao] 找到content: {content_text[:100]}")
                                                    # 过滤掉中间状态消息
                                                    if not any(ignore in content_text for ignore in ignore_texts):
                                                        response_text += content_text
                                                    else:
                                                        logger.debug(f"[Doubao] 过滤掉状态消息: {content_text}")

                                                # 提取图片
                                                if "attachments" in msg:
                                                    for att in msg["attachments"]:
                                                        if att.get("type") == "image" and att.get("url"):
                                                            image_urls.append(att["url"])
                                                            logger.debug(f"[Doubao] 找到图片: {att['url'][:100]}")

                                            # 提取纯文本字段
                                            elif "text" in event_data:
                                                text = event_data["text"]
                                                logger.debug(f"[Doubao] 找到text: {text[:100]}")
                                                if not any(ignore in text for ignore in ignore_texts):
                                                    response_text += text

                                        except (json.JSONDecodeError, TypeError, KeyError) as e:
                                            logger.debug(f"[Doubao] 解析event_data失败: {e}")
                                            pass

                                    # 处理直接的text字段（非event_data）
                                    if "text" in data and "event_data" not in data:
                                        text = data["text"]
                                        logger.debug(f"[Doubao] 找到直接text: {text[:100]}")
                                        if not any(ignore in text for ignore in ignore_texts):
                                            response_text += text

                                except json.JSONDecodeError as e:
                                    logger.debug(f"[Doubao] JSON解析失败: {e}, line: {line[:100]}")
                                    continue

                        # 如果没有解析到内容，尝试正则提取
                        if not response_text:
                            import re
                            # 查找所有"content":"xxx"或"text":"xxx"
                            content_pattern = r'"content"\s*:\s*"([^"]+)"'
                            text_pattern = r'"text"\s*:\s*"([^"]+)"'

                            content_matches = re.findall(content_pattern, content)
                            text_matches = re.findall(text_pattern, content)

                            all_texts = content_matches + text_matches
                            # 过滤掉状态消息
                            filtered_texts = [t for t in all_texts if not any(ignore in t for ignore in ignore_texts)]

                            if filtered_texts:
                                response_text = " ".join(filtered_texts)
                            else:
                                logger.warning(f"[Doubao] 未能解析出有效文本内容")
                                response_text = content[:500] if content else "豆包API返回了空响应"

                    except Exception as parse_err:
                        logger.error(f"[Doubao] 响应解析失败: {parse_err}")
                        response_text = f"解析响应失败: {str(parse_err)}"

                    # 如果检测到异步任务但没有提取到图片，轮询获取结果
                    # 注意：历史API可能返回404，优先依赖直接从流中解析
                    if async_task_id and not image_urls:
                        logger.info(f"[Doubao] 流中未找到图片，尝试轮询异步任务: {async_task_id}")
                        response_text, image_urls = await self._poll_async_task(async_task_id)

                    logger.info(f"[Doubao] 解析结果: 文本长度={len(response_text)}, 图片数={len(image_urls)}")
                    return response_text, image_urls

        except Exception as e:
            logger.error(f"[Doubao] 请求失败: {e}")
            raise

    async def _find_image_message_by_timestamp(self, target_timestamp: int, tolerance: int = 10) -> dict:
        """
        根据时间戳从豆包对话历史中查找对应的图片消息

        Args:
            target_timestamp: 目标时间戳
            tolerance: 时间容差（秒），默认10秒

        Returns:
            包含message_id和image_urls的字典，如果未找到返回None
        """
        history_url = "https://www.doubao.com/samantha/api/chat/history"

        url_params = {
            "aid": "497858",
            "device_id": self.device_id,
            "device_platform": "web",
            "language": "zh",
            "pc_version": "2.50.3",
            "pkg_type": "release_version",
            "real_aid": "497858",
            "region": "CN",
            "samantha_web": "1",
            "sys_region": "CN",
            "tea_uuid": self.web_id,
            "use-olympus-account": "1",
            "version_code": "20800",
            "web_id": self.web_id,
        }

        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json",
            "origin": "https://www.doubao.com",
            "referer": f"https://www.doubao.com/chat/{self.conversation_id}",
            "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "cookie": self.cookie,
        }

        payload = {
            "conversation_id": self.conversation_id,
            "limit": 20  # 获取较多消息以提高匹配成功率
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    history_url,
                    params=url_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"[Doubao] 查找时间戳{target_timestamp}的图片消息")

                        # 查找时间戳匹配的bot回复
                        if "messages" in result:
                            for msg in reversed(result["messages"]):  # 从最新的开始
                                if msg.get("role") == "assistant" or msg.get("sender") == "bot":
                                    msg_time = msg.get("create_time", 0)

                                    # 检查时间戳是否在容差范围内
                                    if abs(msg_time - target_timestamp) <= tolerance:
                                        logger.info(f"[Doubao] 找到匹配的消息，message_id: {msg.get('message_id')}, 时间差: {abs(msg_time - target_timestamp)}秒")

                                        # 解析消息中的图片
                                        image_urls = []
                                        if "content_block" in msg:
                                            for block in msg["content_block"]:
                                                if block.get("block_type") == 2074:  # 图片生成块
                                                    content = block.get("content", {})
                                                    if "creation_block" in content:
                                                        creation = content["creation_block"]
                                                        if "creations" in creation:
                                                            for item in creation["creations"]:
                                                                if "image" in item and "image_ori" in item["image"]:
                                                                    url = item["image"]["image_ori"].get("url")
                                                                    if url:
                                                                        image_urls.append(url)
                                                                        logger.debug(f"[Doubao] 提取图片URL: {url[:100]}")

                                        if image_urls:
                                            return {
                                                "message_id": msg.get("message_id"),
                                                "image_urls": image_urls
                                            }

                        logger.warning(f"[Doubao] 未找到时间戳{target_timestamp}对应的图片消息")
                        return None
                    else:
                        error_text = await response.text()
                        logger.warning(f"[Doubao] 获取历史失败: {response.status}, {error_text[:200]}")
                        return None

        except Exception as e:
            logger.error(f"[Doubao] 查找图片消息出错: {e}")
            return None

    async def _get_recent_image_urls_from_history(self, limit: int = 4) -> list:
        """
        从豆包对话历史中获取最近生成的图片URL（已废弃，保留用于兼容）

        Args:
            limit: 获取的消息数量

        Returns:
            图片URL列表
        """
        history_url = "https://www.doubao.com/samantha/api/chat/history"

        url_params = {
            "aid": "497858",
            "device_id": self.device_id,
            "device_platform": "web",
            "language": "zh",
            "pc_version": "2.50.3",
            "pkg_type": "release_version",
            "real_aid": "497858",
            "region": "CN",
            "samantha_web": "1",
            "sys_region": "CN",
            "tea_uuid": self.web_id,
            "use-olympus-account": "1",
            "version_code": "20800",
            "web_id": self.web_id,
        }

        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "content-type": "application/json",
            "origin": "https://www.doubao.com",
            "referer": f"https://www.doubao.com/chat/{self.conversation_id}",
            "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            "cookie": self.cookie,
        }

        payload = {
            "conversation_id": self.conversation_id,
            "limit": limit * 2  # 多获取一些，确保能找到图片
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    history_url,
                    params=url_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        logger.debug(f"[Doubao] 历史响应: {str(result)[:500]}")

                        image_urls = []
                        # 查找最新的包含图片的bot回复
                        if "messages" in result:
                            for msg in reversed(result["messages"]):  # 从最新的开始
                                if msg.get("role") == "assistant" or msg.get("sender") == "bot":
                                    # 解析消息中的图片
                                    if "content_block" in msg:
                                        for block in msg["content_block"]:
                                            if block.get("block_type") == 2074:  # 图片生成块
                                                content = block.get("content", {})
                                                if "creation_block" in content:
                                                    creation = content["creation_block"]
                                                    if "creations" in creation:
                                                        for item in creation["creations"]:
                                                            if "image" in item and "image_ori" in item["image"]:
                                                                url = item["image"]["image_ori"].get("url")
                                                                if url:
                                                                    image_urls.append(url)
                                                                    logger.debug(f"[Doubao] 从历史提取图片URL: {url[:100]}")

                                    # 如果找到图片，返回
                                    if image_urls:
                                        return image_urls[:limit]

                        return image_urls
                    else:
                        error_text = await response.text()
                        logger.warning(f"[Doubao] 获取历史失败: {response.status}, {error_text[:200]}")
                        return []

        except Exception as e:
            logger.error(f"[Doubao] 获取历史出错: {e}")
            return []

    async def _poll_async_task(self, task_id: str, max_retries: int = 10) -> tuple:
        """
        等待异步任务完成并获取对话历史

        Args:
            task_id: 异步任务ID
            max_retries: 最大重试次数

        Returns:
            (回复文本, 图片URL列表)
        """
        # 等待豆包生成回复（每次等待3秒，最多10次=30秒）
        for retry in range(max_retries):
            logger.debug(f"[Doubao] 等待异步任务完成 (尝试 {retry+1}/{max_retries})")
            await asyncio.sleep(3)

            # 获取对话历史的最新消息
            history_url = "https://www.doubao.com/samantha/api/chat/history"

            url_params = {
                "aid": "497858",
                "device_id": self.device_id,
                "device_platform": "web",
                "language": "zh",
                "pc_version": "2.50.3",
                "pkg_type": "release_version",
                "real_aid": "497858",
                "region": "CN",
                "samantha_web": "1",
                "sys_region": "CN",
                "tea_uuid": self.web_id,
                "use-olympus-account": "1",
                "version_code": "20800",
                "web_id": self.web_id,
            }

            headers = {
                "accept": "*/*",
                "accept-language": "zh-CN,zh;q=0.9",
                "content-type": "application/json",
                "origin": "https://www.doubao.com",
                "referer": f"https://www.doubao.com/chat/{self.conversation_id}",
                "sec-ch-ua": '"Not;A=Brand";v="24", "Chromium";v="128"',
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": '"Windows"',
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
                "cookie": self.cookie,
            }

            payload = {
                "conversation_id": self.conversation_id,
                "limit": 5  # 获取最近5条消息
            }

            try:
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        history_url,
                        params=url_params,
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=10)
                    ) as response:
                        if response.status == 200:
                            result = await response.json()
                            logger.debug(f"[Doubao] 历史响应: {str(result)[:500]}")

                            # 查找最新的bot回复
                            if "messages" in result:
                                for msg in reversed(result["messages"]):  # 从最新的开始
                                    # 查找bot的回复消息
                                    if msg.get("role") == "assistant" or msg.get("sender") == "bot":
                                        return self._parse_history_message(msg)

                            # 如果没找到，继续等待
                            logger.debug(f"[Doubao] 未找到bot回复，继续等待")
                        else:
                            error_text = await response.text()
                            logger.warning(f"[Doubao] 获取历史失败: {response.status}, {error_text[:200]}")

            except Exception as e:
                logger.warning(f"[Doubao] 获取历史出错: {e}")

        # 超时
        logger.error(f"[Doubao] 异步任务等待超时")
        return "豆包响应超时，请稍后重试", []

    def _parse_history_message(self, msg: dict) -> tuple:
        """
        解析历史消息（支持新旧版API格式）

        Returns:
            (回复文本, 图片URL列表)
        """
        response_text = ""
        image_urls = []

        try:
            # 新版API: 使用 content_block 数组
            if "content_block" in msg:
                for block in msg["content_block"]:
                    block_type = block.get("block_type")
                    content = block.get("content", {})

                    # block_type 10000: 文本块
                    if block_type == 10000 and "text_block" in content:
                        text = content["text_block"].get("text", "")
                        if text:
                            response_text += text

                    # block_type 2074: 图片生成块
                    elif block_type == 2074 and "creation_block" in content:
                        creation = content["creation_block"]
                        # 从创作块中提取图片URL
                        if "result" in creation and "image_urls" in creation["result"]:
                            urls = creation["result"]["image_urls"]
                            image_urls.extend(urls)
                        # 或者从 artifacts 中提取
                        elif "artifacts" in creation:
                            for artifact in creation["artifacts"]:
                                if artifact.get("type") == "image" and "url" in artifact:
                                    image_urls.append(artifact["url"])

            # 旧版API: 使用简单的 content 和 attachments
            else:
                # 提取文本内容
                if "content" in msg:
                    content = msg["content"]
                    if isinstance(content, str):
                        try:
                            content_obj = json.loads(content)
                            if "text" in content_obj:
                                response_text = content_obj["text"]
                            else:
                                response_text = content
                        except json.JSONDecodeError:
                            response_text = content
                    else:
                        response_text = str(content)

                # 提取图片
                if "attachments" in msg:
                    for att in msg["attachments"]:
                        if att.get("type") == "image" and att.get("url"):
                            image_urls.append(att["url"])

            logger.info(f"[Doubao] 从历史中解析到回复: 文本长度={len(response_text)}, 图片数={len(image_urls)}")

        except Exception as e:
            logger.error(f"[Doubao] 解析历史消息失败: {e}")
            logger.error(f"[Doubao] 消息结构: {str(msg)[:500]}")
            response_text = "解析回复失败"

        return response_text, image_urls

    def get_help_text(self, **kwargs):
        """返回帮助文本"""
        help_text = "豆包AI助手\n\n"

        # 对话功能
        if "chat" in self.commands:
            chat_cmds = ' 或 '.join(self.commands["chat"][:3])
            help_text += f"💬 对话: {chat_cmds} + 你的问题\n"
            help_text += f"   例如: {self.commands['chat'][0]} 今天天气怎么样？\n\n"

        # 超能模式
        if self.enable_super_mode and "super" in self.commands:
            super_cmds = ' 或 '.join(self.commands["super"][:2])
            help_text += f"🚀 超能模式: {super_cmds} + 复杂任务\n"
            help_text += f"   例如: {self.commands['super'][0]} 设计一个英语学习网站方案\n\n"

        # 音乐生成
        if self.enable_music and "music" in self.commands:
            music_cmds = ' 或 '.join(self.commands["music"][:2])
            help_text += f"🎵 音乐生成: {music_cmds} + 主题/歌词\n"
            help_text += f"   例如: {self.commands['music'][0]} 写一首关于春天的歌\n\n"

        # 播客生成
        if self.enable_podcast and "podcast" in self.commands:
            podcast_cmds = ' 或 '.join(self.commands["podcast"][:2])
            help_text += f"🎙️ 播客生成: {podcast_cmds} + 链接/PDF\n"
            help_text += f"   例如: {self.commands['podcast'][0]} https://example.com/article\n"

        return help_text.strip()

    async def _generate_music(self, prompt: str) -> tuple:
        """
        生成音乐

        Args:
            prompt: 音乐主题或歌词描述

        Returns:
            (回复文本, 音频URL列表)
        """
        import uuid
        import time

        logger.info(f"[Doubao] 开始生成音乐: {prompt[:100]}")
        start_time = time.time()

        base_url = "https://www.doubao.com/samantha/chat/completion"

        # URL参数
        url_params = {
            "aid": "497858",
            "device_id": self.device_id,
            "device_platform": "web",
            "language": "zh",
            "pc_version": "2.50.3",
            "pkg_type": "release_version",
            "real_aid": "497858",
            "region": "CN",
            "samantha_web": "1",
            "sys_region": "CN",
            "tea_uuid": self.web_id,
            "use-olympus-account": "1",
            "version_code": "20800",
            "web_id": self.web_id,
        }

        # 请求头
        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "agw-js-conv": "str, str",
            "content-type": "application/json",
            "origin": "https://www.doubao.com",
            "referer": f"https://www.doubao.com/chat/{self.conversation_id}",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "cookie": self.cookie,
        }

        # 生成UUID
        local_message_id = str(uuid.uuid4())

        # 构建请求体（音乐生成格式 - 匹配真实curl命令）
        # 根据真实API，除了text，其他字段都设为空字符串，让豆包自动处理
        payload = {
            "messages": [
                {
                    "local_message_id": local_message_id,
                    "content": json.dumps({
                        "text": prompt,  # 用户的自然语言描述
                        "lyric": "",     # 空字符串，豆包自动处理
                        "theme": "",     # 空字符串，豆包自动处理
                        "mood": "",      # 空字符串，豆包自动处理
                        "genre": "",     # 空字符串，豆包自动处理
                        "gender": "",    # 空字符串，豆包自动处理
                        "generation_type": ""  # 空字符串，豆包自动处理
                    }),
                    "content_type": 2005  # 音乐生成内容类型
                }
            ],
            "completion_option": {
                "is_regen": False,
                "with_suggest": True,
                "need_create_conversation": False,
                "launch_stage": 1,
                "is_replace": False,
                "is_delete": False,
                "is_ai_playground": False,
                "message_from": 0,
                "action_bar_skill_id": 9,  # 音乐生成技能ID
                "use_auto_cot": False,
                "resend_for_regen": False,
                "enable_commerce_credit": False,
                "event_id": "0"
            },
            "evaluate_option": {
                "web_ab_params": ""
            },
            "section_id": "",
            "conversation_id": self.conversation_id,
            "local_message_id": local_message_id  # 添加到顶层
        }

        # 发送请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    base_url,
                    params=url_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=120)
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"音乐生成API请求失败: {response.status}, {error_text[:200]}")

                    # 读取SSE响应
                    sse_lines = []
                    buffer = b""

                    async for chunk in response.content.iter_any():
                        buffer += chunk
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            line_text = line_bytes.decode('utf-8', errors='ignore').strip()
                            if line_text:
                                sse_lines.append(line_text)
                                if '"event_type":2003' in line_text:
                                    logger.debug(f"[Doubao] 音乐生成完成")
                                    break
                        else:
                            continue
                        break

                    content = '\n'.join(sse_lines)
                    logger.debug(f"[Doubao] 音乐生成响应: {content[:1000]}")

                    # 解析音频URL
                    audio_urls = []
                    response_text = "音乐生成成功"

                    try:
                        lines = content.strip().split('\n')
                        for line in lines:
                            if not line or line.startswith(':'):
                                continue

                            if line.startswith('data: '):
                                json_str = line[6:]
                                try:
                                    data = json.loads(json_str)

                                    # 查找音频URL（可能在多个位置）
                                    if "music_url" in data:
                                        audio_urls.append(data["music_url"])
                                    elif "audio_url" in data:
                                        audio_urls.append(data["audio_url"])
                                    elif "url" in data and data["url"].endswith(('.mp3', '.wav', '.m4a')):
                                        audio_urls.append(data["url"])

                                    # 提取文本信息
                                    if "event_data" in data:
                                        try:
                                            event_data = json.loads(data["event_data"])
                                            if "message" in event_data and "content" in event_data["message"]:
                                                response_text = event_data["message"]["content"]
                                        except:
                                            pass

                                except json.JSONDecodeError:
                                    continue

                    except Exception as parse_err:
                        logger.error(f"[Doubao] 音乐响应解析失败: {parse_err}")

                    api_time = time.time() - start_time
                    logger.info(f"[Doubao] 音乐生成完成，耗时: {api_time:.2f}秒，音频数: {len(audio_urls)}")

                    return response_text, audio_urls

        except Exception as e:
            logger.error(f"[Doubao] 音乐生成失败: {e}")
            # 降级到对话模式
            logger.warning("[Doubao] 降级到对话模式生成音乐")
            return await self._chat_with_doubao(f"帮我创作音乐: {prompt}", use_super_mode=False)

    async def _generate_podcast(self, prompt: str) -> tuple:
        """
        生成播客

        Args:
            prompt: 网页链接、PDF路径或文本内容

        Returns:
            (回复文本, 音频URL列表)
        """
        import uuid
        import time
        import re

        logger.info(f"[Doubao] 开始生成播客: {prompt[:100]}")
        start_time = time.time()

        base_url = "https://www.doubao.com/samantha/chat/completion"

        # URL参数
        url_params = {
            "aid": "497858",
            "device_id": self.device_id,
            "device_platform": "web",
            "language": "zh",
            "pc_version": "2.50.3",
            "pkg_type": "release_version",
            "real_aid": "497858",
            "region": "CN",
            "samantha_web": "1",
            "sys_region": "CN",
            "tea_uuid": self.web_id,
            "use-olympus-account": "1",
            "version_code": "20800",
            "web_id": self.web_id,
        }

        # 请求头
        headers = {
            "accept": "*/*",
            "accept-language": "zh-CN,zh;q=0.9",
            "agw-js-conv": "str, str",
            "content-type": "application/json",
            "origin": "https://www.doubao.com",
            "referer": f"https://www.doubao.com/chat/{self.conversation_id}",
            "sec-ch-ua": '"Chromium";v="140", "Not=A?Brand";v="24"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36",
            "cookie": self.cookie,
        }

        # 生成UUID
        local_message_id = str(uuid.uuid4())

        # 检测是否是URL
        url_pattern = r'https?://[^\s]+'
        url_match = re.search(url_pattern, prompt)

        # 构建消息内容和附件
        attachments = []
        if url_match:
            # 如果有URL，提取URL作为附件，文本作为指令
            url = url_match.group(0)
            # 移除URL后的文本作为指令，如果为空则使用默认指令
            instruction = prompt.replace(url, "").strip()
            if not instruction:
                instruction = "简短点"  # 默认指令：生成简短版播客

            message_content = {"text": instruction}
            attachments.append({
                "type": "link",
                "key": url,
                "url": url
            })
            logger.info(f"[Doubao] 检测到链接: {url}，指令: {instruction}")
        else:
            # 如果没有URL，直接使用prompt作为文本内容
            message_content = {"text": prompt}

        # 构建请求体（播客生成格式 - 匹配curl命令格式）
        message_obj = {
            "content": json.dumps(message_content),
            "content_type": 2034,  # 播客生成内容类型
        }

        if attachments:
            message_obj["attachments"] = attachments

        payload = {
            "messages": [message_obj],
            "completion_option": {
                "is_regen": False,
                "with_suggest": True,
                "need_create_conversation": False,
                "launch_stage": 1,
                "is_replace": False,
                "is_delete": False,
                "is_ai_playground": False,
                "message_from": 0,
                "action_bar_skill_id": 26,  # 播客生成技能ID
                "use_auto_cot": False,
                "resend_for_regen": False,
                "enable_commerce_credit": False,
                "event_id": "0"
            },
            "evaluate_option": {
                "web_ab_params": ""
            },
            "section_id": "",
            "conversation_id": self.conversation_id,
            "local_message_id": local_message_id  # 添加到顶层
        }

        # 发送请求
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    base_url,
                    params=url_params,
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=180)  # 播客生成可能较慢
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"播客生成API请求失败: {response.status}, {error_text[:200]}")

                    # 读取SSE响应
                    sse_lines = []
                    buffer = b""

                    async for chunk in response.content.iter_any():
                        buffer += chunk
                        while b'\n' in buffer:
                            line_bytes, buffer = buffer.split(b'\n', 1)
                            line_text = line_bytes.decode('utf-8', errors='ignore').strip()
                            if line_text:
                                sse_lines.append(line_text)
                                if '"event_type":2003' in line_text:
                                    logger.debug(f"[Doubao] 播客生成完成")
                                    break
                        else:
                            continue
                        break

                    content = '\n'.join(sse_lines)
                    logger.debug(f"[Doubao] 播客生成响应前1000字符: {content[:1000]}")
                    # 保存完整响应到文件以便调试
                    try:
                        import os
                        debug_dir = os.path.join(os.path.dirname(__file__), "debug")
                        os.makedirs(debug_dir, exist_ok=True)
                        debug_file = os.path.join(debug_dir, f"podcast_response_{int(time.time())}.txt")
                        with open(debug_file, 'w', encoding='utf-8') as f:
                            f.write(content)
                        logger.info(f"[Doubao] 完整播客响应已保存到: {debug_file}")
                    except Exception as save_err:
                        logger.warning(f"[Doubao] 保存响应文件失败: {save_err}")

                    # 解析音频URL和文本
                    audio_urls = []
                    response_text = "播客生成成功"

                    try:
                        lines = content.strip().split('\n')
                        for line in lines:
                            if not line or line.startswith(':'):
                                continue

                            if line.startswith('data: '):
                                json_str = line[6:]
                                try:
                                    data = json.loads(json_str)
                                    logger.debug(f"[Doubao] 播客解析data: {str(data)[:300]}")

                                    # 方法1: 查找简单的音频URL字段
                                    if "podcast_url" in data:
                                        audio_urls.append(data["podcast_url"])
                                        logger.info(f"[Doubao] 从podcast_url提取音频")
                                    elif "audio_url" in data:
                                        audio_urls.append(data["audio_url"])
                                        logger.info(f"[Doubao] 从audio_url提取音频")
                                    elif "url" in data and data["url"].endswith(('.mp3', '.wav', '.m4a')):
                                        audio_urls.append(data["url"])
                                        logger.info(f"[Doubao] 从url提取音频")

                                    # 方法2: 从patch_op中提取（类似图片生成）
                                    if "patch_op" in data and "message_id" in data:
                                        for patch in data["patch_op"]:
                                            if "patch_value" in patch and "content_block" in patch["patch_value"]:
                                                for block in patch["patch_value"]["content_block"]:
                                                    block_type = block.get("block_type")
                                                    logger.debug(f"[Doubao] 播客block_type: {block_type}")

                                                    # 尝试常见的播客/音频block_type
                                                    # 2005: 音乐, 2034: 播客, 2100+: 可能的其他媒体类型
                                                    if block_type in [2005, 2034, 2100, 2101, 2102, 2035, 2036]:
                                                        logger.info(f"[Doubao] 检测到播客/音频block_type: {block_type}")
                                                        logger.debug(f"[Doubao] 播客block完整结构: {json.dumps(block, ensure_ascii=False)[:1500]}")

                                                        content_obj = block.get("content", {})

                                                        # 从creation_block提取
                                                        if "creation_block" in content_obj:
                                                            creation = content_obj["creation_block"]

                                                            # 查找各种可能的音频URL字段
                                                            if "audio_url" in creation:
                                                                audio_urls.append(creation["audio_url"])
                                                                logger.info(f"[Doubao] 从creation_block.audio_url提取音频")
                                                            elif "url" in creation:
                                                                audio_urls.append(creation["url"])
                                                                logger.info(f"[Doubao] 从creation_block.url提取音频")
                                                            elif "result" in creation:
                                                                result = creation["result"]
                                                                if "audio_url" in result:
                                                                    audio_urls.append(result["audio_url"])
                                                                    logger.info(f"[Doubao] 从result.audio_url提取音频")
                                                                elif "url" in result:
                                                                    audio_urls.append(result["url"])
                                                                    logger.info(f"[Doubao] 从result.url提取音频")
                                                                elif "podcast_url" in result:
                                                                    audio_urls.append(result["podcast_url"])
                                                                    logger.info(f"[Doubao] 从result.podcast_url提取音频")

                                                        # 从content中直接提取
                                                        elif "audio_url" in content_obj:
                                                            audio_urls.append(content_obj["audio_url"])
                                                            logger.info(f"[Doubao] 从content.audio_url提取音频")

                                                    # 文本块
                                                    elif block_type == 10000 and "content" in block:
                                                        if "text_block" in block["content"]:
                                                            text = block["content"]["text_block"].get("text", "")
                                                            if text and "生成中" not in text:
                                                                response_text += text

                                    # 方法3: 提取event_data中的信息
                                    if "event_data" in data:
                                        try:
                                            event_data = json.loads(data["event_data"])
                                            if "message" in event_data and "content" in event_data["message"]:
                                                content_text = event_data["message"]["content"]
                                                if content_text and "生成中" not in content_text:
                                                    response_text = content_text
                                        except:
                                            pass

                                except json.JSONDecodeError:
                                    continue

                    except Exception as parse_err:
                        logger.error(f"[Doubao] 播客响应解析失败: {parse_err}")

                    api_time = time.time() - start_time
                    logger.info(f"[Doubao] 播客生成完成，耗时: {api_time:.2f}秒，音频数: {len(audio_urls)}")

                    return response_text, audio_urls

        except Exception as e:
            logger.error(f"[Doubao] 播客生成失败: {e}")
            # 降级到对话模式
            logger.warning("[Doubao] 降级到对话模式生成播客")
            return await self._chat_with_doubao(f"帮我总结这个内容并生成播客脚本: {prompt}", use_super_mode=False)


    async def _recognize_image_for_generation(self, image_path: str) -> str:
        """
        使用视觉模型识别外部图片，生成用于图片生成的详细描述

        Args:
            image_path: 图片路径

        Returns:
            图片的详细描述，如果识别失败返回None
        """
        try:
            import base64
            import os
            from config import conf
            from lib.openai_proxy.openai_proxy_client import OpenAIProxyClient

            # 读取图片并转base64
            with open(image_path, "rb") as f:
                image_data = f.read()
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # 获取图片扩展名
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp'
            }.get(ext, 'image/jpeg')

            # 构建识图prompt
            recognize_prompt = """请详细描述这张图片用于AI图片生成参考，包括：
1. 主要人物/物体的外观特征（发型、服装、姿态、表情、年龄、性别等）
2. 场景和背景环境的详细描述
3. 光线、色调和氛围
4. 构图和视角
5. 艺术风格（写实、动漫、油画等）

描述要详细、具体、专业，适合作为图片生成prompt使用。"""

            # 构建vision消息
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": recognize_prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_base64}"
                        }
                    }
                ]
            }]

            # 使用OpenAI客户端调用视觉模型
            client = OpenAIProxyClient()
            vision_model = conf().get("vision_model", "gpt-4o")

            response = client.chat_completion(
                model=vision_model,
                messages=messages,
                temperature=0.7,
                max_tokens=2000,
                stream=False
            )

            if response.status_code == 200:
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"[Doubao] 外部图片识别成功，描述长度: {len(content)}")
                return content
            else:
                logger.error(f"[Doubao] 图片识别失败，状态码: {response.status_code}")
                return None

        except Exception as e:
            logger.error(f"[Doubao] 图片识别异常: {e}")
            return None
