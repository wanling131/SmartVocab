"""
健康检查 API（部署与演示用）
"""

import logging
import time
from flask import Blueprint, g

from tools.database import get_database_context
from .utils import APIResponse, handle_api_error

logger = logging.getLogger(__name__)

# 可选导入 psutil（用于系统监控）
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

health_bp = Blueprint("health", __name__, url_prefix="/api")


@health_bp.route("/health", methods=["GET"])
@handle_api_error
def health():
    """轻量存活探测，不访问数据库。"""
    return APIResponse.success({"status": "ok"}, "服务正常")


@health_bp.route("/health/db", methods=["GET"])
@handle_api_error
def health_db():
    """数据库连通性检查。"""
    try:
        with get_database_context() as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
        return APIResponse.success({"status": "ok", "database": "connected"}, "数据库正常")
    except Exception as e:
        logger.warning("健康检查数据库失败: %s", e)
        return APIResponse.error(f"数据库不可用: {e}", 503)


@health_bp.route("/health/cache", methods=["GET"])
@handle_api_error
def health_cache():
    """缓存状态检查。"""
    try:
        from tools.memory_cache import get_all_cache_stats
        stats = get_all_cache_stats()

        # 计算总体统计
        total_hits = sum(s.get("hits", 0) for s in stats.values())
        total_misses = sum(s.get("misses", 0) for s in stats.values())
        total_requests = total_hits + total_misses
        overall_hit_rate = (total_hits / total_requests * 100) if total_requests > 0 else 0

        return APIResponse.success({
            "status": "ok",
            "caches": stats,
            "summary": {
                "total_hits": total_hits,
                "total_misses": total_misses,
                "overall_hit_rate": f"{overall_hit_rate:.2f}%"
            }
        }, "缓存状态正常")
    except Exception as e:
        logger.warning("缓存状态检查失败: %s", e)
        return APIResponse.error(f"缓存不可用: {e}", 503)


@health_bp.route("/health/cache/clear", methods=["POST"])
@handle_api_error
def clear_cache():
    """清除所有缓存（仅用于测试/调试）。"""
    try:
        from tools.memory_cache import (
            word_cache, word_list_cache, user_records_cache,
            recommendation_cache, user_stats_cache, level_config_cache
        )

        word_cache.clear()
        word_list_cache.clear()
        user_records_cache.clear()
        recommendation_cache.clear()
        user_stats_cache.clear()
        level_config_cache.clear()

        return APIResponse.success({"status": "ok"}, "缓存已清除")
    except Exception as e:
        logger.warning("清除缓存失败: %s", e)
        return APIResponse.error(f"清除缓存失败: {e}", 500)


@health_bp.route("/health/metrics", methods=["GET"])
@handle_api_error
def metrics():
    """
    系统指标端点（用于监控和调试）。
    返回数据库连接池、缓存、内存等关键指标。
    """
    try:
        # 数据库连接池状态
        from tools.database import get_pool_status
        pool_status = get_pool_status()

        # 缓存统计
        from tools.memory_cache import get_all_cache_stats
        cache_stats = get_all_cache_stats()

        # 系统资源
        system_info = {"available": PSUTIL_AVAILABLE}
        if PSUTIL_AVAILABLE:
            process = psutil.Process()
            memory_info = process.memory_info()
            system_info.update({
                "memory_mb": round(memory_info.rss / 1024 / 1024, 2),
                "cpu_percent": process.cpu_percent(interval=0.1)
            })

        return APIResponse.success({
            "database": {
                "pool_size": pool_status.get("pool_size", 0),
                "active_connections": pool_status.get("active", 0),
                "idle_connections": pool_status.get("idle", 0)
            },
            "cache": cache_stats,
            "system": system_info,
            "request": {
                "request_id": getattr(g, 'request_id', 'N/A')
            }
        }, "指标获取成功")
    except Exception as e:
        logger.warning("获取系统指标失败: %s", e)
        return APIResponse.error(f"获取指标失败: {e}", 500)


@health_bp.route("/health/slow-queries", methods=["GET"])
@handle_api_error
def slow_queries():
    """
    慢查询日志端点（用于性能分析）。
    返回最近记录的慢查询信息。
    """
    try:
        # 从应用日志中获取慢查询（如果有的话）
        # 这里返回一个占位响应，实际实现需要查询日志存储
        return APIResponse.success({
            "queries": [],
            "message": "慢查询日志功能需要配置日志存储"
        }, "查询成功")
    except Exception as e:
        logger.warning("获取慢查询失败: %s", e)
        return APIResponse.error(f"获取失败: {e}", 500)
