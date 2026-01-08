"""
ImgBB图床上传工具类
支持自动上传图片并返回链接
ImgBB在国内可访问，比Imgur更稳定
"""
import os
import base64
import requests
from common.log import logger


class ImgBBUploader:
    """ImgBB图床上传工具"""

    # ImgBB上传API
    UPLOAD_URL = "https://api.imgbb.com/1/upload"

    # 默认API Key（建议用户申请自己的）
    # 获取方式：https://api.imgbb.com/
    DEFAULT_API_KEY = "9e1e6f85702f6e08cff98bbf90a4fe5a"

    def __init__(self, api_key=None):
        """
        初始化上传器

        Args:
            api_key: ImgBB API Key，如不提供则使用默认Key
        """
        self.api_key = api_key or self.DEFAULT_API_KEY

    def upload_file(self, file_path, timeout=30):
        """
        上传本地图片文件到ImgBB

        Args:
            file_path: 本地图片文件路径
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式：
                {
                    "success": True/False,
                    "link": "https://i.ibb.co/xxx/image.jpg",  # 图片链接
                    "display_url": "https://i.ibb.co/xxx/image.jpg",  # 显示链接
                    "delete_url": "https://ibb.co/xxx/delete",  # 删除链接
                    "error": "错误信息"  # 失败时的错误信息
                }
        """
        if not os.path.exists(file_path):
            logger.error(f"[ImgBBUploader] 文件不存在: {file_path}")
            return {"success": False, "error": "文件不存在"}

        # 检查文件大小（ImgBB限制32MB）
        file_size = os.path.getsize(file_path)
        if file_size > 32 * 1024 * 1024:
            logger.error(f"[ImgBBUploader] 文件过大: {file_size} bytes (最大32MB)")
            return {"success": False, "error": f"文件过大 ({file_size/1024/1024:.2f}MB)，最大支持32MB"}

        try:
            # 读取图片并转换为base64
            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # 准备上传数据
            payload = {
                "key": self.api_key,
                "image": image_data
            }

            # 发送上传请求
            logger.info(f"[ImgBBUploader] 开始上传图片: {file_path} ({file_size/1024:.2f}KB)")
            response = requests.post(
                self.UPLOAD_URL,
                data=payload,
                timeout=timeout
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    url = data.get("url")
                    display_url = data.get("display_url")
                    delete_url = data.get("delete_url")

                    # 优先使用display_url，如果不存在则使用url
                    link = display_url or url

                    logger.info(f"[ImgBBUploader] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "url": url,
                        "display_url": display_url,
                        "delete_url": delete_url
                    }
                else:
                    error_msg = result.get("error", {}).get("message", "未知错误")
                    logger.error(f"[ImgBBUploader] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"[ImgBBUploader] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[ImgBBUploader] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[ImgBBUploader] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}

    def upload_bytes(self, image_bytes, timeout=30):
        """
        上传字节数据到ImgBB

        Args:
            image_bytes: 图片字节数据
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式同upload_file
        """
        try:
            # 检查数据大小
            if len(image_bytes) > 32 * 1024 * 1024:
                logger.error(f"[ImgBBUploader] 数据过大: {len(image_bytes)} bytes (最大32MB)")
                return {"success": False, "error": "数据过大，最大支持32MB"}

            # 转换为base64
            image_data = base64.b64encode(image_bytes).decode('utf-8')

            # 准备上传数据
            payload = {
                "key": self.api_key,
                "image": image_data
            }

            # 发送上传请求
            logger.info(f"[ImgBBUploader] 开始上传图片数据: {len(image_bytes)/1024:.2f}KB")
            response = requests.post(
                self.UPLOAD_URL,
                data=payload,
                timeout=timeout
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    url = data.get("url")
                    display_url = data.get("display_url")
                    delete_url = data.get("delete_url")

                    # 优先使用display_url，如果不存在则使用url
                    link = display_url or url

                    logger.info(f"[ImgBBUploader] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "url": url,
                        "display_url": display_url,
                        "delete_url": delete_url
                    }
                else:
                    error_msg = result.get("error", {}).get("message", "未知错误")
                    logger.error(f"[ImgBBUploader] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"[ImgBBUploader] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[ImgBBUploader] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[ImgBBUploader] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
_uploader_instance = None


def get_imgbb_uploader(api_key=None):
    """
    获取ImgBB上传器单例

    Args:
        api_key: ImgBB API Key（可选）

    Returns:
        ImgBBUploader实例
    """
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = ImgBBUploader(api_key)
    return _uploader_instance
