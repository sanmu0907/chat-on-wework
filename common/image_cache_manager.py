import os
import json
import time
import shutil
import threading
from datetime import datetime
from common.log import logger


class ImageCacheManager:
    """图片缓存管理器，用于长期保存和管理图片文件"""

    def __init__(self, cache_dir="tmp/image_cache", expire_days=3):
        """
        初始化图片缓存管理器

        Args:
            cache_dir: 缓存目录
            expire_days: 过期天数，超过该天数的图片将被清理
        """
        self.cache_dir = cache_dir
        self.expire_days = expire_days
        self.expire_seconds = expire_days * 24 * 3600
        self.index_file = os.path.join(cache_dir, "index.json")
        self.index = {}
        self.lock = threading.Lock()

        # 创建缓存目录
        os.makedirs(cache_dir, exist_ok=True)

        # 加载索引
        self._load_index()

        # 启动清理线程
        self._start_cleanup_thread()

        logger.info(f"[ImageCacheManager] 初始化完成，缓存目录: {cache_dir}, 过期时间: {expire_days}天")

    def _load_index(self):
        """从文件加载索引"""
        try:
            if os.path.exists(self.index_file):
                with open(self.index_file, "r", encoding="utf-8") as f:
                    self.index = json.load(f)
                logger.info(f"[ImageCacheManager] 加载索引成功，共{len(self.index)}条记录")
            else:
                self.index = {}
                logger.info("[ImageCacheManager] 索引文件不存在，创建新索引")
        except Exception as e:
            logger.error(f"[ImageCacheManager] 加载索引失败: {str(e)}")
            self.index = {}

    def _save_index(self):
        """保存索引到文件"""
        try:
            with self.lock:
                with open(self.index_file, "w", encoding="utf-8") as f:
                    json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[ImageCacheManager] 保存索引失败: {str(e)}")

    def save_image(self, user_id, room_id, image_path):
        """
        保存图片到缓存

        Args:
            user_id: 用户ID
            room_id: 群组ID
            image_path: 原始图片路径

        Returns:
            缓存的图片路径
        """
        try:
            if not os.path.exists(image_path):
                logger.error(f"[ImageCacheManager] 原始图片不存在: {image_path}")
                return None

            # 生成缓存文件名
            timestamp = int(time.time())
            ext = os.path.splitext(image_path)[1] or ".jpg"
            cache_filename = f"{user_id}_{timestamp}{ext}"
            cache_path = os.path.join(self.cache_dir, cache_filename)

            # 复制图片到缓存目录
            shutil.copy2(image_path, cache_path)

            # 更新索引 - 使用包含时间戳的key，支持多张图片
            cache_key = f"{user_id}_{room_id}_{timestamp}"
            with self.lock:
                self.index[cache_key] = {
                    "path": cache_path,
                    "timestamp": timestamp,
                    "user_id": user_id,
                    "room_id": room_id,
                    "original_path": image_path
                }

            # 保存索引
            self._save_index()

            file_size = os.path.getsize(cache_path)
            logger.info(f"[ImageCacheManager] 图片已缓存: {cache_filename}, 大小: {file_size} bytes, cache_key: {cache_key}")

            return cache_path

        except Exception as e:
            logger.error(f"[ImageCacheManager] 保存图片失败: {str(e)}")
            return None

    def get_image(self, user_id, room_id, skip_latest=0):
        """
        获取用户的缓存图片

        Args:
            user_id: 用户ID
            room_id: 群组ID
            skip_latest: 跳过最新的N张图片，默认0(返回最新图片)，1表示返回倒数第二张

        Returns:
            图片路径，如果不存在返回None
        """
        try:
            # 查找所有匹配的图片记录
            prefix = f"{user_id}_{room_id}_"
            matched_records = []

            with self.lock:
                for cache_key, cache_info in self.index.items():
                    if cache_key.startswith(prefix):
                        # 检查是否过期
                        timestamp = cache_info["timestamp"]
                        age = time.time() - timestamp

                        if age < self.expire_seconds:
                            # 检查文件是否存在
                            cache_path = cache_info["path"]
                            if os.path.exists(cache_path):
                                matched_records.append({
                                    "key": cache_key,
                                    "path": cache_path,
                                    "timestamp": timestamp,
                                    "age": age
                                })
                            else:
                                logger.warning(f"[ImageCacheManager] 缓存图片文件不存在: {cache_path}")
                        else:
                            logger.debug(f"[ImageCacheManager] 缓存图片已过期: {cache_info['path']}, 年龄: {age/86400:.1f}天")

                # 按时间戳降序排序(最新的在前面)
                matched_records.sort(key=lambda x: x["timestamp"], reverse=True)

                # 根据 skip_latest 参数返回相应的图片
                if len(matched_records) > skip_latest:
                    selected = matched_records[skip_latest]
                    logger.info(f"[ImageCacheManager] 找到缓存图片: {selected['path']}, "
                               f"年龄: {selected['age']/3600:.1f}小时, skip_latest={skip_latest}, "
                               f"总共{len(matched_records)}张图片")
                    return selected["path"]
                else:
                    logger.debug(f"[ImageCacheManager] 未找到足够的缓存图片: user_id={user_id}, room_id={room_id}, "
                                f"skip_latest={skip_latest}, 实际只有{len(matched_records)}张")
                    return None

        except Exception as e:
            logger.error(f"[ImageCacheManager] 获取图片失败: {str(e)}")
            return None

    def cleanup(self):
        """清理过期的缓存文件"""
        try:
            logger.info("[ImageCacheManager] 开始清理过期缓存...")

            current_time = time.time()
            deleted_count = 0
            total_size = 0

            # 清理索引中的过期记录
            with self.lock:
                expired_keys = []
                for cache_key, cache_info in self.index.items():
                    timestamp = cache_info["timestamp"]
                    age = current_time - timestamp

                    if age > self.expire_seconds:
                        expired_keys.append(cache_key)
                        cache_path = cache_info["path"]

                        # 删除文件
                        if os.path.exists(cache_path):
                            file_size = os.path.getsize(cache_path)
                            os.remove(cache_path)
                            deleted_count += 1
                            total_size += file_size
                            logger.debug(f"[ImageCacheManager] 删除过期文件: {cache_path}, 年龄: {age/86400:.1f}天")

                # 从索引中删除过期记录
                for key in expired_keys:
                    del self.index[key]

            # 保存更新后的索引
            if expired_keys:
                self._save_index()

            # 清理缓存目录中不在索引中的孤立文件
            orphan_count = 0
            orphan_size = 0

            if os.path.exists(self.cache_dir):
                indexed_paths = {info["path"] for info in self.index.values()}

                for filename in os.listdir(self.cache_dir):
                    if filename == "index.json":
                        continue

                    filepath = os.path.join(self.cache_dir, filename)

                    if os.path.isfile(filepath) and filepath not in indexed_paths:
                        # 检查文件年龄
                        file_age = current_time - os.path.getmtime(filepath)

                        if file_age > self.expire_seconds:
                            file_size = os.path.getsize(filepath)
                            os.remove(filepath)
                            orphan_count += 1
                            orphan_size += file_size
                            logger.debug(f"[ImageCacheManager] 删除孤立文件: {filename}")

            total_deleted = deleted_count + orphan_count
            total_freed = total_size + orphan_size

            if total_deleted > 0:
                logger.info(f"[ImageCacheManager] 清理完成: 删除{deleted_count}个索引文件 + {orphan_count}个孤立文件，"
                          f"共释放{total_freed/1024/1024:.2f}MB空间")
            else:
                logger.info("[ImageCacheManager] 清理完成: 无过期文件")

        except Exception as e:
            logger.error(f"[ImageCacheManager] 清理缓存失败: {str(e)}")

    def _start_cleanup_thread(self):
        """启动定期清理线程"""
        def cleanup_worker():
            while True:
                try:
                    # 每天清理一次
                    time.sleep(86400)
                    self.cleanup()
                except Exception as e:
                    logger.error(f"[ImageCacheManager] 清理线程异常: {str(e)}")

        cleanup_thread = threading.Thread(target=cleanup_worker, daemon=True)
        cleanup_thread.start()
        logger.info("[ImageCacheManager] 清理线程已启动，每24小时清理一次")

    def get_cache_stats(self):
        """获取缓存统计信息"""
        try:
            with self.lock:
                total_files = len(self.index)

                total_size = 0
                for cache_info in self.index.values():
                    cache_path = cache_info["path"]
                    if os.path.exists(cache_path):
                        total_size += os.path.getsize(cache_path)

                return {
                    "total_files": total_files,
                    "total_size_mb": total_size / 1024 / 1024,
                    "cache_dir": self.cache_dir,
                    "expire_days": self.expire_days
                }
        except Exception as e:
            logger.error(f"[ImageCacheManager] 获取统计信息失败: {str(e)}")
            return {}


# 全局单例
_image_cache_manager = None


def get_image_cache_manager():
    """获取图片缓存管理器单例"""
    global _image_cache_manager
    if _image_cache_manager is None:
        _image_cache_manager = ImageCacheManager()
    return _image_cache_manager
