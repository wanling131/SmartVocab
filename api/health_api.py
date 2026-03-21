"""
健康检查 API（部署与演示用）
"""

import logging
from flask import Blueprint

from tools.database import get_database_context
from .utils import APIResponse, handle_api_error

logger = logging.getLogger(__name__)

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
