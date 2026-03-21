"""
API基础工具模块
提供统一的响应格式和错误处理
"""

import logging
from flask import jsonify
from functools import wraps

from config import APP_CONFIG

logger = logging.getLogger(__name__)


class APIResponse:
    """API响应工具类"""
    
    @staticmethod
    def success(data=None, message="操作成功", status_code=200):
        """创建成功响应"""
        response = {
            'success': True,
            'message': message,
            'data': data
        }
        return jsonify(response), status_code
    
    @staticmethod
    def error(message="操作失败", status_code=400, data=None):
        """创建错误响应"""
        response = {
            'success': False,
            'message': message,
            'data': data
        }
        return jsonify(response), status_code

def handle_api_error(func):
    """
    API 错误处理装饰器。
    生产环境（EXPOSE_ERROR_DETAILS=False）不向客户端返回异常详情，避免信息泄露。
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logger.exception("未处理异常 in %s: %s", func.__qualname__, e)
            if APP_CONFIG.get("expose_error_details"):
                return APIResponse.error(f"服务器错误: {str(e)}", 500)
            return APIResponse.error("服务器内部错误，请稍后重试", 500)
    return wrapper
