"""
管理员权限检查工具
"""

import logging
import os

logger = logging.getLogger(__name__)

# 管理员配置：通过环境变量 ADMIN_USERS 指定，逗号分隔的用户名列表
ADMIN_USERS: set = set(u.strip() for u in os.getenv("ADMIN_USERS", "").split(",") if u.strip())


def is_admin(username: str = None) -> bool:
    """
    检查用户是否为管理员。

    Args:
        username: 要检查的用户名，如果为 None 则从当前请求获取。

    Returns:
        bool: 是否为管理员。
    """
    if not ADMIN_USERS:
        logger.warning("ADMIN_USERS 未配置，拒绝管理员操作。请在 .env 中设置 ADMIN_USERS")
        return False

    if username is None:
        # 从请求上下文获取当前用户
        try:
            from api.auth_middleware import get_current_user

            current = get_current_user()
            if not current:
                return False
            username = current.get("username")
        except Exception:
            return False

    return username in ADMIN_USERS


def check_admin_access() -> tuple:
    """
    检查管理员权限并返回错误响应（用于 API 端点）。

    Returns:
        tuple: 如果不是管理员返回 (error_response, 403)，否则返回 None。
    """
    from api.utils import APIResponse

    if not ADMIN_USERS:
        return APIResponse.error("ADMIN_USERS 未配置，请在 .env 中设置", 500)

    try:
        from api.auth_middleware import get_current_user

        current = get_current_user()
        if not current:
            return APIResponse.error("请先登录", 401)

        if current.get("username") not in ADMIN_USERS:
            return APIResponse.error("需要管理员权限", 403)
    except Exception:
        return APIResponse.error("权限检查失败", 500)

    return None
