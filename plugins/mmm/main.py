from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api import logger
import random
import aiohttp
import tempfile

IMAGE_APIS = [
    "https://api.btstu.cn/sjbz/api.php?lx=dongman&format=images&method=mobile&lx=meizi",
    "https://cdn.seovx.com/?mom=302",
    "https://api.mhimg.cn/api/girls_img/?type=img",
    "https://api.mhimg.cn/api/Welfare_img/"
]

NEW_IMAGE_API = "http://api.yujn.cn/api/heisi.php"  # 新接口：黑丝
JK_API = "http://api.yujn.cn/api/jk.php?"
YOUHUO_API = "http://api.yujn.cn/api/yht.php"
BAISI_API = "http://api.yujn.cn/api/baisi.php"

@register("mm_plugin", "your_name", "发送美图的插件", "1.0.0", "repo_url")
class MMPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        self.config = self.context.get_config()
        if "enable" not in self.config:
            self.config["enable"] = True
        if "triggers" not in self.config:
            self.config["triggers"] = ["666", "黑丝"]
        self.config.save_config()
        # 动态注册命令和消息监听
        filter.command("666")(self.send_beauty_image)
        filter.command("黑丝")(self.send_heisi_image)
        filter.command("jk")(self.send_jk_image)
        filter.command("诱惑")(self.send_youhuo_image)
        filter.command("白丝")(self.send_baisi_image)
        logger.info("[DEBUG] mm_plugin 插件初始化并注册监听器")

    @filter.event_message_type(filter.EventMessageType.ALL)
    async def keyword_trigger(self, event: AstrMessageEvent):
        """关键词触发处理器"""
        logger.info(f"[DEBUG] mm_plugin on_message 触发: {event.get_message_str()}，is_private: {event.is_private_chat()}，group_id: {event.get_group_id()}，user_id: {event.get_sender_id()}")
        if not self.config["enable"]:
            return
        msg = event.get_message_str()
        if "666" in msg:
            for img_url in random.sample(IMAGE_APIS, len(IMAGE_APIS)):
                async with aiohttp.ClientSession() as session:
                    try:
                        async with session.get(img_url, timeout=8, allow_redirects=True) as resp:
                            content_type = resp.headers.get("Content-Type", "")
                            if isinstance(content_type, bytes):
                                content_type = content_type.decode()
                            content_type = str(content_type)
                            if resp.status == 200 and content_type.startswith("image/"):
                                img_bytes = await resp.read()
                                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                    tmp_file.write(img_bytes)
                                    tmp_path = tmp_file.name
                                yield event.image_result(tmp_path)
                                event.stop_event()
                                return
                    except Exception as e:
                        logger.error(f"请求图片API异常: {img_url} error={e}")
            yield event.plain_result("图片接口暂时不可用，请稍后再试。")
            event.stop_event()
            return
        elif "黑丝" in msg:
            async with aiohttp.ClientSession() as session:
                img_bytes = await self.fetch_image_with_redirect(session, NEW_IMAGE_API)
                if img_bytes:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                        tmp_file.write(img_bytes)
                        tmp_path = tmp_file.name
                    yield event.image_result(tmp_path)
                    event.stop_event()
                    return
                else:
                    logger.warning(f"黑丝API未获取到图片内容: {NEW_IMAGE_API}")
            yield event.plain_result("黑丝图片接口暂时不可用，请稍后再试。")
            event.stop_event()
            return
        elif "jk" in msg:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(JK_API, timeout=8) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            img_url = data.get("data") or data.get("url") or data.get("image") or data.get("img")
                            if img_url:
                                img_bytes = await self.fetch_image_with_redirect(session, img_url)
                                if img_bytes:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                        tmp_file.write(img_bytes)
                                        tmp_path = tmp_file.name
                                    yield event.image_result(tmp_path)
                                    event.stop_event()
                                    return
                except Exception as e:
                    logger.error(f"jk API异常: {JK_API} error={e}")
            yield event.plain_result("jk图片接口暂时不可用，请稍后再试。")
            event.stop_event()
            return
        elif "诱惑" in msg:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(YOUHUO_API, timeout=8) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            img_url = data.get("data") or data.get("url") or data.get("image") or data.get("img")
                            if img_url:
                                img_bytes = await self.fetch_image_with_redirect(session, img_url)
                                if img_bytes:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                        tmp_file.write(img_bytes)
                                        tmp_path = tmp_file.name
                                    yield event.image_result(tmp_path)
                                    event.stop_event()
                                    return
                except Exception as e:
                    logger.error(f"诱惑API异常: {YOUHUO_API} error={e}")
            yield event.plain_result("诱惑图片接口暂时不可用，请稍后再试。")
            event.stop_event()
            return
        elif "白丝" in msg:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(BAISI_API, timeout=8) as resp:
                        if resp.status == 200:
                            data = await resp.json()
                            img_url = data.get("data") or data.get("url") or data.get("image") or data.get("img")
                            if img_url:
                                img_bytes = await self.fetch_image_with_redirect(session, img_url)
                                if img_bytes:
                                    with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                        tmp_file.write(img_bytes)
                                        tmp_path = tmp_file.name
                                    yield event.image_result(tmp_path)
                                    event.stop_event()
                                    return
                except Exception as e:
                    logger.error(f"白丝API异常: {BAISI_API} error={e}")
            yield event.plain_result("白丝图片接口暂时不可用，请稍后再试。")
            event.stop_event()
            return

    async def send_beauty_image(self, event: AstrMessageEvent):
        logger.info(f"[DEBUG] mm_plugin command 666 触发: {event.get_message_str()}")
        logger.info(f"[DEBUG] 来源: {'私聊' if event.is_private_chat() else '群聊'}，群号: {event.get_group_id()}，用户: {event.get_sender_id()}")
        if not self.config["enable"]:
            return
        for img_url in random.sample(IMAGE_APIS, len(IMAGE_APIS)):
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(img_url, timeout=8, allow_redirects=True) as resp:
                        content_type = resp.headers.get("Content-Type", "")
                        if isinstance(content_type, bytes):
                            content_type = content_type.decode()
                        content_type = str(content_type)
                        logger.info(f"content_type type: {type(content_type)} value: {content_type}")
                        if resp.status == 200 and content_type.startswith("image/"):
                            img_bytes = await resp.read()
                            logger.info(f"触发美图发送: {resp.url}")
                            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                                tmp_file.write(img_bytes)
                                tmp_path = tmp_file.name
                            yield event.image_result(tmp_path)
                            event.stop_event()
                            return
                        else:
                            logger.warning(f"API返回非图片内容: {img_url} status={resp.status} content-type={content_type}")
                except Exception as e:
                    logger.error(f"请求图片API异常: {img_url} error={e}")
        yield event.plain_result("图片接口暂时不可用，请稍后再试。")
        event.stop_event()
        return

    async def fetch_image_with_redirect(self, session, url, max_redirects=3):
        for _ in range(max_redirects):
            async with session.get(url, timeout=8, allow_redirects=False) as resp:
                content_type = resp.headers.get("Content-Type", "")
                if isinstance(content_type, bytes):
                    content_type = content_type.decode()
                content_type = str(content_type)
                if resp.status == 200 and content_type.startswith("image/"):
                    return await resp.read()
                elif resp.status in (301, 302) or "Location" in resp.headers or "location" in resp.headers:
                    url = resp.headers.get("Location") or resp.headers.get("location")
                    if not url:
                        break
                else:
                    break
        return None

    async def send_heisi_image(self, event: AstrMessageEvent):
        logger.info(f"[DEBUG] mm_plugin command 黑丝 触发: {event.get_message_str()}")
        if not self.config["enable"]:
            return
        async with aiohttp.ClientSession() as session:
            img_bytes = await self.fetch_image_with_redirect(session, NEW_IMAGE_API)
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(img_bytes)
                    tmp_path = tmp_file.name
                yield event.image_result(tmp_path)
                event.stop_event()
                return
            else:
                logger.warning(f"黑丝API未获取到图片内容: {NEW_IMAGE_API}")
        yield event.plain_result("黑丝图片接口暂时不可用，请稍后再试。")
        event.stop_event()
        return

    async def send_jk_image(self, event: AstrMessageEvent):
        logger.info(f"[DEBUG] mm_plugin command jk 触发: {event.get_message_str()}")
        if not self.config["enable"]:
            return
        async with aiohttp.ClientSession() as session:
            img_bytes = await self.fetch_image_with_redirect(session, JK_API)
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(img_bytes)
                    tmp_path = tmp_file.name
                yield event.image_result(tmp_path)
                event.stop_event()
                return
            else:
                logger.warning(f"jk API未获取到图片内容: {JK_API}")
        yield event.plain_result("jk图片接口暂时不可用，请稍后再试。")
        event.stop_event()
        return

    async def send_youhuo_image(self, event: AstrMessageEvent):
        logger.info(f"[DEBUG] mm_plugin command 诱惑 触发: {event.get_message_str()}")
        if not self.config["enable"]:
            return
        async with aiohttp.ClientSession() as session:
            img_bytes = await self.fetch_image_with_redirect(session, YOUHUO_API)
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(img_bytes)
                    tmp_path = tmp_file.name
                yield event.image_result(tmp_path)
                event.stop_event()
                return
            else:
                logger.warning(f"诱惑API未获取到图片内容: {YOUHUO_API}")
        yield event.plain_result("诱惑图片接口暂时不可用，请稍后再试。")
        event.stop_event()
        return

    async def send_baisi_image(self, event: AstrMessageEvent):
        logger.info(f"[DEBUG] mm_plugin command 白丝 触发: {event.get_message_str()}")
        if not self.config["enable"]:
            return
        async with aiohttp.ClientSession() as session:
            img_bytes = await self.fetch_image_with_redirect(session, BAISI_API)
            if img_bytes:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp_file:
                    tmp_file.write(img_bytes)
                    tmp_path = tmp_file.name
                yield event.image_result(tmp_path)
                event.stop_event()
                return
            else:
                logger.warning(f"白丝API未获取到图片内容: {BAISI_API}")
        yield event.plain_result("白丝图片接口暂时不可用，请稍后再试。")
        event.stop_event()
        return 