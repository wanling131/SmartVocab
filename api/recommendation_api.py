"""
推荐系统API模块
提供智能单词推荐功能接口
"""

from flask import Blueprint, request

from config import LEARNING_PARAMS
from core.recommendation.recommendation_engine import RecommendationEngine
from tools.memory_cache import make_recommendation_key

from .auth_middleware import check_user_access, require_auth
from .utils import APIResponse, handle_api_error

# 创建蓝图
recommendation_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")

# 初始化推荐引擎
recommendation_engine = RecommendationEngine()


@recommendation_bp.route("/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_recommendations(user_id):
    """获取推荐单词"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    limit = request.args.get("limit", LEARNING_PARAMS["default_recommendation_limit"], type=int)
    algorithm = request.args.get("algorithm", "mixed")
    refresh = request.args.get("refresh", "false").lower() == "true"

    # 如果请求刷新，清除缓存
    if refresh:
        from tools.memory_cache import recommendation_cache
        cache_key = make_recommendation_key(user_id, algorithm, limit)
        recommendation_cache.delete(cache_key)

    # 直接获取请求数量的推荐
    recommendations = recommendation_engine.get_recommendations(user_id, limit, algorithm)
    return APIResponse.success(recommendations, "获取推荐成功")
