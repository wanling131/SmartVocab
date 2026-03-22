"""
推荐系统API模块
提供智能单词推荐功能接口
"""

from flask import Blueprint, request
from core.recommendation.recommendation_engine import RecommendationEngine
from config import LEARNING_PARAMS
from .utils import APIResponse, handle_api_error
from .auth_middleware import require_auth, get_current_user

# 创建蓝图
recommendation_bp = Blueprint('recommendations', __name__, url_prefix='/api/recommendations')

# 初始化推荐引擎
recommendation_engine = RecommendationEngine()


def _check_user_access(user_id):
    """检查当前用户是否有权访问指定用户的数据"""
    current_user = get_current_user()
    if not current_user or current_user.get('user_id') != user_id:
        return False
    return True


@recommendation_bp.route('/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_recommendations(user_id):
    """获取推荐单词"""
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    limit = request.args.get('limit', LEARNING_PARAMS["default_recommendation_limit"], type=int)
    algorithm = request.args.get('algorithm', 'mixed')

    # 直接获取请求数量的推荐
    recommendations = recommendation_engine.get_recommendations(user_id, limit, algorithm)
    return APIResponse.success(recommendations, "获取推荐成功")
