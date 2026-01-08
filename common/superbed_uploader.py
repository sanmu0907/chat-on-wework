"""
Superbed图床上传工具类
支持自动上传图片并返回链接
Superbed在微信中可以正常打开
"""
import os
import requests
from common.log import logger


class SuperbedUploader:
    """Superbed图床上传工具"""

    # Superbed上传API
    UPLOAD_URL = "https://www.superbed.cn/api/upload"

    def __init__(self):
        """初始化上传器"""
        pass

    def upload_file(self, file_path, timeout=30):
        """
        上传本地图片文件到Superbed

        Args:
            file_path: 本地图片文件路径
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式：
                {
                    "success": True/False,
                    "link": "https://pic.superbed.cn/item/xxx.jpg",  # 图片链接
                    "error": "错误信息"  # 失败时的错误信息
                }
        """
        if not os.path.exists(file_path):
            logger.error(f"[SuperbedUploader] 文件不存在: {file_path}")
            return {"success": False, "error": "文件不存在"}

        # 检查文件大小（Superbed限制10MB）
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            logger.error(f"[SuperbedUploader] 文件过大: {file_size} bytes (最大10MB)")
            return {"success": False, "error": f"文件过大 ({file_size/1024/1024:.2f}MB)，最大支持10MB"}

        try:
            # 准备上传数据
            with open(file_path, "rb") as image_file:
                files = {
                    'file': (os.path.basename(file_path), image_file, 'image/jpeg')
                }

                # 发送上传请求
                logger.info(f"[SuperbedUploader] 开始上传图片: {file_path} ({file_size/1024:.2f}KB)")
                response = requests.post(
                    self.UPLOAD_URL,
                    files=files,
                    timeout=timeout
                )

                # 解析响应
                if response.status_code == 200:
                    result = response.json()
                    
                    # Superbed返回格式：{"err": 0, "url": "https://pic.superbed.cn/item/xxx.jpg"}
                    if result.get("err") == 0:
                        url = result.get("url")
                        logger.info(f"[SuperbedUploader] 上传成功: {url}")
                        return {
                            "success": True,
                            "link": url
                        }
                    else:
                        error_msg = result.get("msg", "未知错误")
                        logger.error(f"[SuperbedUploader] 上传失败: {error_msg}")
                        return {"success": False, "error": error_msg}
                else:
                    error_msg = f"HTTP {response.status_code}: {response.text}"
                    logger.error(f"[SuperbedUploader] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[SuperbedUploader] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[SuperbedUploader] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
_uploader_instance = None


def get_superbed_uploader():
    """
    获取Superbed上传器单例

    Returns:
        SuperbedUploader实例
    """
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = SuperbedUploader()
    return _uploader_instance
