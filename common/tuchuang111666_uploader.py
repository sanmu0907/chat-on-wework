# encoding:utf-8
"""
111666.best图床上传工具类
API配置: https://i.111666.best/image
参考: https://www.nodeseek.com/post-316630-1
"""
import os
import requests
from common.log import logger


class Tuchuang111666Uploader:
    """111666.best图床上传工具（匿名上传，无需登录）"""

    UPLOAD_URL = "https://i.111666.best/image"
    BASE_URL = "https://i.111666.best"

    def __init__(self, auth_token=None):
        """
        初始化上传器（匿名模式）
        """
        self.headers = {
            "Accept": "application/json",
        }
        logger.info("[Tuchuang111666] 初始化完成（匿名上传模式）")

    def upload_file(self, file_path, timeout=30):
        """
        上传本地图片文件到111666.best

        Args:
            file_path: 本地图片文件路径
            timeout: 上传超时时间（秒）

        Returns:
            dict: 上传结果，格式：
                {
                    "success": True/False,
                    "link": "https://i.111666.best/xxx.jpg",
                    "delete_url": "xxx",
                    "error": "错误信息"
                }
        """
        if not os.path.exists(file_path):
            logger.error(f"[Tuchuang111666] 文件不存在: {file_path}")
            return {"success": False, "error": "文件不存在"}

        # 检查文件大小（限制10MB）
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:
            logger.error(f"[Tuchuang111666] 文件过大: {file_size} bytes (最大10MB)")
            return {"success": False, "error": f"文件过大 ({file_size/1024/1024:.2f}MB)，最大支持10MB"}

        try:
            # 准备文件
            filename = os.path.basename(file_path)

            # 获取MIME类型
            ext = os.path.splitext(filename)[1].lower()
            mime_types = {
                '.jpg': 'image/jpeg',
                '.jpeg': 'image/jpeg',
                '.png': 'image/png',
                '.gif': 'image/gif',
                '.webp': 'image/webp',
                '.bmp': 'image/bmp'
            }
            mime_type = mime_types.get(ext, 'image/jpeg')

            with open(file_path, "rb") as f:
                # 参数名为 image
                files = {"image": (filename, f, mime_type)}

                # 发送上传请求
                logger.info(f"[Tuchuang111666] 开始上传图片: {file_path} ({file_size/1024:.2f}KB)")
                response = requests.post(
                    self.UPLOAD_URL,
                    headers=self.headers,
                    files=files,
                    timeout=timeout
                )

            # 解析响应
            logger.debug(f"[Tuchuang111666] 响应状态码: {response.status_code}")
            logger.debug(f"[Tuchuang111666] 响应内容: {response.text[:500]}")

            if response.status_code == 200:
                result = response.json()

                # 111666.best返回格式: {"src": "/xxx.jpg"} 或其他格式
                if "src" in result:
                    # 拼接完整URL
                    src = result.get("src")
                    if src.startswith("/"):
                        link = f"{self.BASE_URL}{src}"
                    elif src.startswith("http"):
                        link = src
                    else:
                        link = f"{self.BASE_URL}/{src}"

                    logger.info(f"[Tuchuang111666] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "delete_url": result.get("delete_url")
                    }
                elif "url" in result:
                    # 备选字段
                    link = result.get("url")
                    logger.info(f"[Tuchuang111666] 上传成功: {link}")
                    return {
                        "success": True,
                        "link": link,
                        "delete_url": result.get("delete_url")
                    }
                elif "data" in result and isinstance(result["data"], dict):
                    # 可能是嵌套格式
                    data = result["data"]
                    link = data.get("src") or data.get("url") or data.get("link")
                    if link:
                        if link.startswith("/"):
                            link = f"{self.BASE_URL}{link}"
                        logger.info(f"[Tuchuang111666] 上传成功: {link}")
                        return {
                            "success": True,
                            "link": link,
                            "delete_url": data.get("delete_url")
                        }

                # 无法解析响应格式
                error_msg = result.get("message") or result.get("error") or result.get("msg") or "未知响应格式"
                logger.error(f"[Tuchuang111666] 上传失败: {error_msg}, 响应: {result}")
                return {"success": False, "error": error_msg}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                logger.error(f"[Tuchuang111666] 上传失败: {error_msg}")
                return {"success": False, "error": error_msg}

        except requests.exceptions.Timeout:
            logger.error(f"[Tuchuang111666] 上传超时")
            return {"success": False, "error": "上传超时"}
        except Exception as e:
            logger.error(f"[Tuchuang111666] 上传异常: {str(e)}")
            return {"success": False, "error": str(e)}


# 全局单例
_uploader_instance = None


def get_tuchuang111666_uploader(auth_token=None):
    """
    获取111666.best上传器单例

    Args:
        auth_token: Auth Token（可选）

    Returns:
        Tuchuang111666Uploader实例
    """
    global _uploader_instance
    if _uploader_instance is None:
        _uploader_instance = Tuchuang111666Uploader(auth_token)
    return _uploader_instance
