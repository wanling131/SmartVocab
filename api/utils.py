"""
API基础工具模块
提供统一的响应格式和错误处理
"""

from flask import jsonify
from functools import wraps

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
    """API错误处理装饰器"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            return APIResponse.error(f'服务器错误: {str(e)}', 500)
    return wrapper
