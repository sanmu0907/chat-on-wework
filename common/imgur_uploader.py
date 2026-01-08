"""
Imgur图床上传工具类
支持自动上传图片并返回链接
"""
import os
import base64
import requests
from common.log import logger


class ImgurUploader:
    """Imgur图床上传工具"""

    # Imgur匿名上传API（无需注册，但有速率限制）
    # 如果需要更高的上传限制，可以注册Imgur应用并使用Client ID
    UPLOAD_URL = "https://api.imgur.com/3/upload"

    # 默认使用公共Client ID（建议用户申请自己的）
    # 获取方式：https://api.imgur.com/oauth2/addclient
    DEFAULT_CLIENT_ID = "546c25a59c58ad7"  # 公共测试ID，建议替换

    def __init__(self, client_id=None):
        """
        初始化上传器

        Args:
            client_id: Imgur Client ID，如不提供则使用默认ID
        """
        self.client_id = client_id or self.DEFAULT_CLIENT_ID
        self.headers = {
            "Authorization": f"Client-ID {self.client_id}"
        }

    def upload_file(self, file_path, timeout=30):
        """
        上传本地图片文件到Imgur

        Args:
            file_path: 本地图片文件路径
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式：
                {
                    "success": True/False,
                    "link": "https://i.imgur.com/xxx.jpg",  # 图片链接
                    "delete_hash": "xxx",  # 删除哈希（可用于删除图片）
                    "error": "错误信息"  # 失败时的错误信息
                }
        """
        if not os.path.exists(file_path):
            logger.error(f"[ImgurUploader] 文件不存在: {file_path}")
            return {"success": False, "error": "文件不存在"}

        # 检查文件大小（Imgur限制10MB）
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            logger.error(f"[ImgurUploader] 文件过大: {file_size} bytes (最大10MB)")
            return {"success": False, "error": f"文件过大 ({file_size/1024/1024:.2f}MB)，最大支持10MB"}

        try:
            # 读取图片并转换为base64
            with open(file_path, "rb") as image_file:
                image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # 准备上传数据
            payload = {
                "image": image_data,
                "type": "base64"
            }

            # 发送上传请求
            logger.info(f"[ImgurUploader] 开始上传图片: {file_path} ({file_size/1024:.2f}KB)")
            response = requests.post(
                self.UPLOAD_URL,
                headers=self.headers,
                data=payload,
                timeout=timeout
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    link = data.get("link")
                    delete_hash = data.get("deletehash")

                    logger.info(f"[ImgurUploader] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "delete_hash": delete_hash
                    }
                else:
                    error_msg = result.get("data", {}).get("error", "未知错误")
                    logger.error(f"[ImgurUploader] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"[ImgurUploader] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[ImgurUploader] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[ImgurUploader] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}

    def upload_bytes(self, image_bytes, timeout=30):
        """
        上传字节数据到Imgur

        Args:
            image_bytes: 图片字节数据
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式同upload_file
        """
        try:
            # 检查数据大小
            if len(image_bytes) > 10 * 1024 * 1024:
                logger.error(f"[ImgurUploader] 数据过大: {len(image_bytes)} bytes (最大10MB)")
                return {"success": False, "error": "数据过大，最大支持10MB"}

            # 转换为base64
            image_data = base64.b64encode(image_bytes).decode('utf-8')

            # 准备上传数据
            payload = {
                "image": image_data,
                "type": "base64"
            }

            # 发送上传请求
            logger.info(f"[ImgurUploader] 开始上传图片数据: {len(image_bytes)/1024:.2f}KB")
            response = requests.post(
                self.UPLOAD_URL,
                headers=self.headers,
                data=payload,
                timeout=timeout
            )

            # 解析响应
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    data = result.get("data", {})
                    link = data.get("link")
                    delete_hash = data.get("deletehash")

                    logger.info(f"[ImgurUploader] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "delete_hash": delete_hash
                    }
                else:
                    error_msg = result.get("data", {}).get("error", "未知错误")
                    logger.error(f"[ImgurUploader] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                logger.error(f"[ImgurUploader] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[ImgurUploader] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[ImgurUploader] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
_uploader_instance = None


def get_imgur_uploader(client_id=None):
    """
    获取Imgur上传器单例

    Args:
        client_id: Imgur Client ID（可选）

    Returns:
        ImgurUploader实例
    """
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = ImgurUploader(client_id)
    return _uploader_instance
