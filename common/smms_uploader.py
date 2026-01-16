# encoding:utf-8
"""
SM.MS图床上传工具类
API文档: https://doc.sm.ms/
"""
import os
import requests
from common.log import logger


class SmmsUploader:
    """SM.MS图床上传工具"""

    UPLOAD_URL = "https://sm.ms/api/v2/upload"

    def __init__(self, api_token=None):
        """
        初始化上传器

        Args:
            api_token: SM.MS API Token（可选，不提供则匿名上传）
        """
        self.api_token = api_token
        self.headers = {}
        # 只有当token看起来像SM.MS token时才添加（SM.MS token通常较长）
        if api_token and len(api_token) > 40:
            self.headers["Authorization"] = api_token
            logger.info("[SmmsUploader] 使用Token认证模式")
        else:
            logger.info("[SmmsUploader] 使用匿名上传模式")

    def upload_file(self, file_path, timeout=30):
        """
        上传本地图片文件到SM.MS

        Args:
            file_path: 本地图片文件路径
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式：
                {
                    "success": True/False,
                    "link": "https://s2.loli.net/xxx.jpg",
                    "delete_url": "xxx",
                    "error": "错误信息"
                }
        """
        if not os.path.exists(file_path):
            logger.error(f"[SmmsUploader] 文件不存在: {file_path}")
            return {"success": False, "error": "文件不存在"}

        # 检查文件大小（SM.MS限制5MB）
        file_size = os.path.getsize(file_path)
        if file_size > 5 * 1024 * 1024:
            logger.error(f"[SmmsUploader] 文件过大: {file_size} bytes (最大5MB)")
            return {"success": False, "error": f"文件过大 ({file_size/1024/1024:.2f}MB)，最大支持5MB"}

        try:
            # 准备文件
            filename = os.path.basename(file_path)
            with open(file_path, "rb") as f:
                files = {"smfile": (filename, f, "image/jpeg")}

                # 发送上传请求
                logger.info(f"[SmmsUploader] 开始上传图片: {file_path} ({file_size/1024:.2f}KB)")
                response = requests.post(
                    self.UPLOAD_URL,
                    headers=self.headers,
                    files=files,
                    timeout=timeout
                )

            # 解析响应
            if response.status_code == 200:
                result = response.json()

                if result.get("success"):
                    data = result.get("data", {})
                    link = data.get("url")
                    delete_url = data.get("delete")

                    logger.info(f"[SmmsUploader] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "delete_url": delete_url
                    }
                else:
                    # SM.MS特殊情况：图片已存在会返回existing链接
                    if result.get("code") == "image_repeated":
                        existing_url = result.get("images")
                        logger.info(f"[SmmsUploader] 图片已存在: {existing_url}")
                        return {
                            "success": True,
                            "link": existing_url,
                            "delete_url": None
                        }

                    error_msg = result.get("message", "未知错误")
                    logger.error(f"[SmmsUploader] 上传失败: {error_msg}")
                    return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"[SmmsUploader] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[SmmsUploader] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[SmmsUploader] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
_uploader_instance = None


def get_smms_uploader(api_token=None):
    """
    获取SM.MS上传器单例

    Args:
        api_token: SM.MS API Token（可选）

    Returns:
        SmmsUploader实例
    """
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = SmmsUploader(api_token)
    return _uploader_instance
