# encoding:utf-8
"""
imgbb.com图床上传工具类
API文档: https://api.imgbb.com/
"""
import os
import base64
import requests
from common.log import logger


class ImgBBUploader:
    """imgbb.com图床上传工具"""

    UPLOAD_URL = "https://api.imgbb.com/1/upload"

    def __init__(self, api_key):
        """
        初始化上传器

        Args:
            api_key: API Key，在 https://api.imgbb.com/ 获取
        """
        self.api_key = api_key
        if not api_key:
            logger.warning("[ImgBB] api_key未配置，上传将会失败")
        else:
            logger.info("[ImgBB] 初始化完成")

    def upload_file(self, file_path, timeout=30):
        """
        上传本地图片文件到imgbb.com

        Args:
            file_path: 本地图片文件路径
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果
        """
        if not self.api_key:
            return {"success": False, "error": "api_key未配置"}

        if not os.path.exists(file_path):
            logger.error(f"[ImgBB] 文件不存在: {file_path}")
            return {"success": False, "error": "文件不存在"}

        # 检查文件大小（限制32MB）
        file_size = os.path.getsize(file_path)
        if file_size > 32 * 1024 * 1024:
            logger.error(f"[ImgBB] 文件过大: {file_size} bytes (最大32MB)")
            return {"success": False, "error": f"文件过大 ({file_size/1024/1024:.2f}MB)，最大支持32MB"}

        try:
            # 读取文件并转为base64
            with open(file_path, "rb") as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # 构建请求
            payload = {
                "key": self.api_key,
                "image": image_data
            }

            logger.info(f"[ImgBB] 开始上传图片: {file_path} ({file_size/1024:.2f}KB)")
            response = requests.post(
                self.UPLOAD_URL,
                data=payload,
                timeout=timeout
            )

            logger.debug(f"[ImgBB] 响应状态码: {response.status_code}")
            logger.debug(f"[ImgBB] 响应内容: {response.text[:500]}")

            if response.status_code == 200:
                result = response.json()

                # imgbb返回格式: {"success": true, "data": {"url": "xxx", ...}}
                if result.get("success"):
                    data = result.get("data", {})
                    link = data.get("url")

                    if link:
                        logger.info(f"[ImgBB] 上传成功: {link}")
                        return {
                            "success": True,
                            "link": link,
                            "thumbnail": data.get("thumb", {}).get("url"),
                            "delete_url": data.get("delete_url")
                        }
                    else:
                        return {"success": False, "error": "响应中无图片URL"}
                else:
                    error = result.get("error", {})
                    error_msg = error.get("message") if isinstance(error, dict) else str(error)
                    logger.error(f"[ImgBB] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg or "上传失败"}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"[ImgBB] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error("[ImgBB] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[ImgBB] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
_uploader_instance = None


def get_imgurl_uploader(api_key=None):
    """
    获取imgbb上传器单例

    Args:
        api_key: API Key

    Returns:
        ImgBBUploader实例
    """
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = ImgBBUploader(api_key)
    return _uploader_instance
