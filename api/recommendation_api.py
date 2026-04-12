"""
推荐系统API模块
提供智能单词推荐功能接口
"""

from flask import Blueprint, request

from config import LEARNING_PARAMS
from core.recommendation.recommendation_engine import RecommendationEngine
from tools.memory_cache import make_recommendation_key, recommendation_cache

from .auth_middleware import check_user_access, require_auth
from .utils import APIResponse, handle_api_error

# 创建蓝图
recommendation_bp = Blueprint("recommendations", __name__, url_prefix="/api/recommendations")

# 初始化推荐引擎
recommendation_engine = RecommendationEngine()

# 推荐池配置：首次获取50词，每页5词，共10页
RECOMMENDATION_POOL_SIZE = 50
RECOMMENDATION_PAGE_SIZE = 5


@recommendation_bp.route("/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_recommendations(user_id):
    """获取推荐单词（分页式刷新）"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    limit = request.args.get("limit", RECOMMENDATION_PAGE_SIZE, type=int)
    algorithm = request.args.get("algorithm", "mixed")
    refresh = request.args.get("refresh", "false").lower() == "true"

    # 分页索引（前端传递）
    page_index = request.args.get("page", 0, type=int)

    # 推荐池缓存键（存储50词的推荐池）
    pool_cache_key = f"rec_pool:{user_id}:{algorithm}:{RECOMMENDATION_POOL_SIZE}"

    # 获取或创建推荐池
    pool = recommendation_cache.get(pool_cache_key)
    total_pages = RECOMMENDATION_POOL_SIZE // limit

    # 刷新或池不存在或翻到最后 -> 重新计算
    need_recompute = refresh or pool is None or page_index >= total_pages

    if need_recompute:
        # 重新计算推荐池（获取50词）
        pool = recommendation_engine.get_recommendations(
            user_id, RECOMMENDATION_POOL_SIZE, algorithm
        )
        recommendation_cache.set(pool_cache_key, pool, ttl=300)
        page_index = 0  # 重置到第一页

    # 从池中取当前页
    start = page_index * limit
    end = start + limit
    page_recommendations = pool[start:end] if pool else []

    # 返回数据包含分页信息
    response_data = {
        "words": page_recommendations,
        "page": page_index,
        "total_pages": total_pages,
        "has_more": page_index < total_pages - 1
    }

    return APIResponse.success(response_data, "获取推荐成功")
