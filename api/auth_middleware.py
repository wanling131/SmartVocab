"""
JWT 认证工具模块
提供 Token 生成、验证和认证装饰器
"""

import os
import logging
from datetime import datetime, timedelta, timezone
from functools import wraps
from flask import request, jsonify

import jwt

from config import APP_CONFIG

logger = logging.getLogger(__name__)

# JWT 配置
JWT_SECRET_KEY = (os.getenv('JWT_SECRET_KEY') or 'smartvocab-jwt-secret-key-change-in-production').strip()
JWT_EXPIRATION_HOURS = int(os.getenv('JWT_EXPIRATION_HOURS', '24'))
JWT_ALGORITHM = 'HS256'

# 弱密钥列表（生产环境禁止使用）
WEAK_KEYS = {
    'smartvocab-jwt-secret-key-change-in-production',
    'please-change-this-jwt-secret-in-production',
    'secret', 'jwt-secret', 'test', 'dev', 'development'
}

# 与 config.APP_CONFIG 一致：production / staging 等均视为生产模式，禁止弱 JWT 密钥
if APP_CONFIG.get('production'):
    if not JWT_SECRET_KEY or JWT_SECRET_KEY in WEAK_KEYS or len(JWT_SECRET_KEY) < 32:
        raise ValueError(
            "生产环境必须设置安全的 JWT_SECRET_KEY 环境变量 "
            "(建议使用 openssl rand -hex 32 生成，至少32字符)"
        )
    logger.info("JWT 生产环境配置校验通过")


def generate_token(user_id: int, username: str) -> str:
    """
    生成 JWT Token

    Args:
        user_id: 用户ID
        username: 用户名

    Returns:
        JWT Token 字符串
    """
    now = datetime.now(timezone.utc)
    payload = {
        'user_id': user_id,
        'username': username,
        'exp': now + timedelta(hours=JWT_EXPIRATION_HOURS),
        'iat': now
    }
    return jwt.encode(payload, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> dict:
    """
    验证 JWT Token

    Args:
        token: JWT Token 字符串

    Returns:
        解码后的 payload，或 None（验证失败）
    """
    try:
        payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token 已过期")
        return None
    except jwt.InvalidTokenError as e:
        logger.warning("Token 无效: %s", e)
        return None


def get_current_user() -> dict:
    """
    从请求头获取当前用户信息

    Returns:
        用户信息字典，或 None（未认证）
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None

    token = auth_header[7:]  # 移除 'Bearer ' 前缀
    payload = verify_token(token)
    return payload


def require_auth(f):
    """
    认证装饰器
    保护需要登录才能访问的 API 端点

    用法:
        @app.route('/protected')
        @require_auth
        def protected_endpoint():
            user = get_current_user()
            return {'user_id': user['user_id']}
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        user = get_current_user()
        if not user:
            return jsonify({
                'success': False,
                'message': '请先登录',
                'error': 'unauthorized'
            }), 401
        return f(*args, **kwargs)
    return decorated


def optional_auth(f):
    """
    可选认证装饰器
    尝试获取用户信息，但不强制要求登录

    用法:
        @app.route('/public')
        @optional_auth
        def public_endpoint():
            user = get_current_user()
            if user:
                # 已登录用户的逻辑
                pass
            else:
                # 未登录用户的逻辑
                pass
    """
    @wraps(f)
    def decorated(*args, **kwargs):
        return f(*args, **kwargs)
    return decorated
