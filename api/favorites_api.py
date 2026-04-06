"""
收藏单词 API
"""

import logging
from flask import Blueprint, request
from tools.favorites_crud import FavoritesCRUD
from .utils import APIResponse, handle_api_error
from .auth_middleware import require_auth, check_user_access

logger = logging.getLogger(__name__)

favorites_bp = Blueprint('favorites', __name__, url_prefix='/api/favorites')
favorites_crud = FavoritesCRUD()


@favorites_bp.route('/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_favorites(user_id):
    """获取用户收藏列表"""
    if not check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    limit = request.args.get('limit', 100, type=int)
    offset = request.args.get('offset', 0, type=int)

    favorites = favorites_crud.get_user_favorites(user_id, limit, offset)
    total = favorites_crud.get_favorite_count(user_id)

    return APIResponse.success({
        'favorites': favorites,
        'total': total
    }, "获取收藏列表成功")


@favorites_bp.route('/<int:user_id>/ids', methods=['GET'])
@handle_api_error
@require_auth
def get_favorite_ids(user_id):
    """获取用户收藏的单词ID列表（快速判断用）"""
    if not check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    ids = favorites_crud.get_favorited_word_ids(user_id)
    return APIResponse.success({'word_ids': ids}, "获取成功")


@favorites_bp.route('/<int:user_id>/word/<int:word_id>', methods=['POST'])
@handle_api_error
@require_auth
def add_favorite(user_id, word_id):
    """添加收藏"""
    if not check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    data = request.get_json() or {}
    note = data.get('note', '')

    # 检查是否已收藏
    if favorites_crud.is_favorited(user_id, word_id):
        return APIResponse.success({'is_favorited': True}, "已收藏")

    record_id = favorites_crud.add_favorite(user_id, word_id, note)
    if record_id:
        return APIResponse.success({'is_favorited': True}, "收藏成功")
    return APIResponse.error('收藏失败', 500)


@favorites_bp.route('/<int:user_id>/word/<int:word_id>', methods=['DELETE'])
@handle_api_error
@require_auth
def remove_favorite(user_id, word_id):
    """取消收藏"""
    if not check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    success = favorites_crud.remove_favorite(user_id, word_id)
    if success:
        return APIResponse.success({'is_favorited': False}, "取消收藏成功")
    return APIResponse.error('取消收藏失败或未收藏', 400)


@favorites_bp.route('/<int:user_id>/word/<int:word_id>', methods=['GET'])
@handle_api_error
@require_auth
def check_favorite(user_id, word_id):
    """检查是否已收藏"""
    if not check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    is_fav = favorites_crud.is_favorited(user_id, word_id)
    return APIResponse.success({'is_favorited': is_fav}, "查询成功")


@favorites_bp.route('/<int:user_id>/word/<int:word_id>/note', methods=['PUT'])
@handle_api_error
@require_auth
def update_note(user_id, word_id):
    """更新收藏备注"""
    if not check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    data = request.get_json() or {}
    note = data.get('note', '')

    success = favorites_crud.update_note(user_id, word_id, note)
    if success:
        return APIResponse.success({}, "备注更新成功")
    return APIResponse.error('更新失败', 400)
