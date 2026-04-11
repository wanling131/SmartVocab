"""
内存缓存模块 - 提供高性能的内存缓存功能
用于缓存频繁访问的数据，减少数据库查询

Features:
- TTL (Time To Live) 过期机制
- LRU (Least Recently Used) 淘汰策略
- 线程安全
- 内存使用限制
- 缓存命中率统计
"""

import logging
import threading
import time
from collections import OrderedDict
from functools import wraps
from typing import Any, Callable, Dict, Optional, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


class CacheEntry:
    """缓存条目"""

    def __init__(self, value: Any, ttl: int):
        self.value = value
        self.created_at = time.time()
        self.ttl = ttl  # 秒
        self.access_count = 0
        self.last_access = self.created_at

    def is_expired(self) -> bool:
        """检查是否过期"""
        if self.ttl <= 0:
            return False
        return time.time() - self.created_at > self.ttl

    def access(self):
        """记录访问"""
        self.access_count += 1
        self.last_access = time.time()


class MemoryCache:
    """
    内存缓存实现
    - TTL过期机制
    - LRU淘汰策略
    - 线程安全
    - 最大条目数限制
    """

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        初始化缓存

        Args:
            max_size: 最大缓存条目数
            default_ttl: 默认过期时间（秒），0表示永不过期
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size
        self._default_ttl = default_ttl

        # 统计信息
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[Any]:
        """
        获取缓存值

        Args:
            key: 缓存键

        Returns:
            缓存值，如果不存在或过期则返回None
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            entry = self._cache[key]

            # 检查是否过期
            if entry.is_expired():
                del self._cache[key]
                self._misses += 1
                logger.debug("缓存过期: %s", key)
                return None

            # LRU: 移到末尾（最近使用）
            self._cache.move_to_end(key)
            entry.access()
            self._hits += 1

            return entry.value

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        设置缓存值

        Args:
            key: 缓存键
            value: 缓存值
            ttl: 过期时间（秒），None使用默认值
        """
        with self._lock:
            # 如果已存在，先删除
            if key in self._cache:
                del self._cache[key]

            # 检查容量，执行LRU淘汰
            while len(self._cache) >= self._max_size:
                oldest_key = next(iter(self._cache))
                del self._cache[oldest_key]
                logger.debug("LRU淘汰: %s", oldest_key)

            # 添加新条目
            actual_ttl = ttl if ttl is not None else self._default_ttl
            self._cache[key] = CacheEntry(value, actual_ttl)

    def delete(self, key: str) -> bool:
        """
        删除缓存

        Args:
            key: 缓存键

        Returns:
            是否成功删除
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()
            self._hits = 0
            self._misses = 0

    def cleanup_expired(self) -> int:
        """
        清理过期缓存

        Returns:
            清理的条目数
        """
        with self._lock:
            expired_keys = [key for key, entry in self._cache.items() if entry.is_expired()]
            for key in expired_keys:
                del self._cache[key]

            if expired_keys:
                logger.debug("清理过期缓存: %d个", len(expired_keys))

            return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            统计信息字典
        """
        with self._lock:
            total_requests = self._hits + self._misses
            hit_rate = self._hits / total_requests * 100 if total_requests > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate": f"{hit_rate:.2f}%",
                "default_ttl": self._default_ttl,
            }

    def get_or_set(self, key: str, factory: Callable[[], T], ttl: Optional[int] = None) -> T:
        """
        获取缓存值，如果不存在则通过factory创建并缓存

        Args:
            key: 缓存键
            factory: 创建值的函数
            ttl: 过期时间

        Returns:
            缓存值或新创建的值
        """
        value = self.get(key)
        if value is not None:
            return value

        value = factory()
        self.set(key, value, ttl)
        return value


# ==================== 全局缓存实例 ====================

# 单词缓存 - 缓存单词详情，TTL 10分钟
word_cache = MemoryCache(max_size=5000, default_ttl=600)

# 词库列表缓存 - 按难度/类型缓存，TTL 5分钟
word_list_cache = MemoryCache(max_size=100, default_ttl=300)

# 用户学习记录缓存 - TTL 2分钟（较短，保证数据实时性）
user_records_cache = MemoryCache(max_size=500, default_ttl=120)

# 推荐结果缓存 - TTL 5分钟
recommendation_cache = MemoryCache(max_size=200, default_ttl=300)

# 用户统计缓存 - TTL 1分钟
user_stats_cache = MemoryCache(max_size=500, default_ttl=60)

# 关卡配置缓存 - TTL 30分钟（变化少）
level_config_cache = MemoryCache(max_size=50, default_ttl=1800)


# ==================== 缓存装饰器 ====================


def cached(cache: MemoryCache, key_prefix: str = "", ttl: Optional[int] = None):
    """
    缓存装饰器

    Args:
        cache: 缓存实例
        key_prefix: 缓存键前缀
        ttl: 过期时间

    Usage:
        @cached(word_cache, "word:")
        def get_word(word_id):
            return db.query(...)
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # 生成缓存键
            cache_key = f"{key_prefix}:{func.__name__}:{args}:{kwargs}"

            # 尝试从缓存获取
            result = cache.get(cache_key)
            if result is not None:
                return result

            # 执行函数并缓存结果
            result = func(*args, **kwargs)
            if result is not None:
                cache.set(cache_key, result, ttl)

            return result

        return wrapper

    return decorator


# ==================== 缓存键生成器 ====================


def make_word_key(word_id: int) -> str:
    """生成单词缓存键"""
    return f"word:{word_id}"


def make_word_list_key(
    dataset_type: str = None, difficulty: int = None, limit: int = None, offset: int = 0
) -> str:
    """生成单词列表缓存键"""
    parts = ["words"]
    if dataset_type:
        parts.append(f"ds:{dataset_type}")
    if difficulty:
        parts.append(f"diff:{difficulty}")
    parts.append(f"limit:{limit or 'all'}")
    parts.append(f"offset:{offset}")
    return ":".join(parts)


def make_user_records_key(user_id: int, limit: int = None, offset: int = 0) -> str:
    """生成用户学习记录缓存键"""
    return f"user_records:{user_id}:limit:{limit or 'all'}:offset:{offset}"


def make_recommendation_key(user_id: int, algorithm: str, limit: int) -> str:
    """生成推荐缓存键"""
    return f"rec:{user_id}:{algorithm}:{limit}"


def make_user_stats_key(user_id: int, days: int = 7) -> str:
    """生成用户统计缓存键"""
    return f"stats:{user_id}:days:{days}"


# ==================== 缓存失效工具 ====================


def invalidate_user_cache(user_id: int) -> None:
    """
    使某个用户相关的所有缓存失效
    在用户完成学习、提交答案后调用
    """
    # 清除用户记录缓存
    keys_to_delete = []
    with user_records_cache._lock:
        for key in user_records_cache._cache.keys():
            if f"user_records:{user_id}:" in key:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del user_records_cache._cache[key]

    # 清除推荐缓存
    keys_to_delete = []
    with recommendation_cache._lock:
        for key in recommendation_cache._cache.keys():
            if f"rec:{user_id}:" in key:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del recommendation_cache._cache[key]

    # 清除统计缓存
    keys_to_delete = []
    with user_stats_cache._lock:
        for key in user_stats_cache._cache.keys():
            if f"stats:{user_id}:" in key:
                keys_to_delete.append(key)
        for key in keys_to_delete:
            del user_stats_cache._cache[key]

    logger.debug("已清除用户 %d 的所有缓存", user_id)


def invalidate_word_cache(word_id: int) -> None:
    """使某个单词的缓存失效"""
    word_cache.delete(make_word_key(word_id))


def get_all_cache_stats() -> Dict[str, Dict[str, Any]]:
    """获取所有缓存的统计信息"""
    return {
        "word_cache": word_cache.get_stats(),
        "word_list_cache": word_list_cache.get_stats(),
        "user_records_cache": user_records_cache.get_stats(),
        "recommendation_cache": recommendation_cache.get_stats(),
        "user_stats_cache": user_stats_cache.get_stats(),
        "level_config_cache": level_config_cache.get_stats(),
    }


def cleanup_all_caches() -> int:
    """清理所有缓存的过期条目"""
    total = 0
    total += word_cache.cleanup_expired()
    total += word_list_cache.cleanup_expired()
    total += user_records_cache.cleanup_expired()
    total += recommendation_cache.cleanup_expired()
    total += user_stats_cache.cleanup_expired()
    total += level_config_cache.cleanup_expired()
    return total


# 定期清理任务（可选，由应用启动时调用）
def start_cache_cleanup_task(interval: int = 300):
    """
    启动定期清理任务

    Args:
        interval: 清理间隔（秒），默认5分钟
    """

    def cleanup_loop():
        while True:
            time.sleep(interval)
            try:
                cleaned = cleanup_all_caches()
                if cleaned > 0:
                    logger.info("定期清理: 清理了 %d 个过期缓存", cleaned)
            except Exception as e:
                logger.error("缓存清理任务失败: %s", e)

    thread = threading.Thread(target=cleanup_loop, daemon=True)
    thread.start()
    logger.info("缓存清理任务已启动，间隔: %d秒", interval)
    return thread
