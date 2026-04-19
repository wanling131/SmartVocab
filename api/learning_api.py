"""
学习记录API模块
提供学习进度、统计、记录查询等功能接口
"""

from flask import Blueprint, request

from config import LEARNING_PARAMS
from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager
from core.learning.learning_record_manager import LearningRecordManager
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager

from .auth_middleware import check_user_access, require_auth
from .utils import APIResponse, handle_api_error

# 创建蓝图
learning_bp = Blueprint("learning", __name__, url_prefix="/api/learning")

# 初始化管理器
vocabulary_manager = VocabularyLearningManager()
learning_record_manager = LearningRecordManager()
forgetting_curve_manager = ForgettingCurveManager()


@learning_bp.route("/progress/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_learning_progress(user_id):
    """获取学习进度"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    progress = vocabulary_manager.get_learning_progress(user_id)
    return APIResponse.success(progress, "获取学习进度成功")


@learning_bp.route("/statistics/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_learning_statistics(user_id):
    """获取学习统计"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    days = request.args.get("days", 7, type=int)
    statistics = vocabulary_manager.get_learning_statistics(user_id, days)
    return APIResponse.success(statistics, "获取学习统计成功")


@learning_bp.route("/records/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_learning_records(user_id):
    """获取学习记录"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    limit = request.args.get("limit", 500, type=int)
    offset = request.args.get("offset", 0, type=int)

    records = learning_record_manager.get_user_learning_records(user_id, limit, offset)
    return APIResponse.success(records, "获取学习记录成功")


@learning_bp.route("/forgetting-curve/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_forgetting_curve(user_id):
    """获取遗忘曲线数据（未来N天复习计划）"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    days = request.args.get("days", LEARNING_PARAMS.get("days_trend_analysis", 7), type=int)
    curve_data = forgetting_curve_manager.get_forgetting_curve_data(user_id, days)
    return APIResponse.success(curve_data, "获取遗忘曲线数据成功")


@learning_bp.route("/review-words/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_review_words(user_id):
    """获取待复习单词列表"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    limit = request.args.get("limit", 100, type=int)
    review_words = forgetting_curve_manager.get_review_words(user_id, limit=limit)
    return APIResponse.success({"words": review_words}, "获取待复习单词成功")


@learning_bp.route("/review-words/<int:user_id>/count", methods=["GET"])
@handle_api_error
@require_auth
def get_review_word_count(user_id):
    """获取待复习单词数量（轻量接口）"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    review_words = forgetting_curve_manager.get_review_words(user_id, limit=10000)
    return APIResponse.success({"count": len(review_words)}, "获取成功")


@learning_bp.route("/record/<int:record_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_learning_record(record_id):
    """获取单条学习记录"""
    from tools.learning_records_crud import LearningRecordsCRUD

    records_crud = LearningRecordsCRUD()
    record = records_crud.read(record_id)
    if not record:
        return APIResponse.error("记录不存在", 404)

    # 验证记录所属用户
    if not check_user_access(record["user_id"]):
        return APIResponse.error("无权访问", 403)

    return APIResponse.success(record, "获取学习记录成功")


@learning_bp.route("/record/<int:record_id>", methods=["PUT"])
@handle_api_error
@require_auth
def update_learning_record(record_id):
    """更新学习记录"""
    from tools.learning_records_crud import LearningRecordsCRUD

    records_crud = LearningRecordsCRUD()

    record = records_crud.read(record_id)
    if not record:
        return APIResponse.error("记录不存在", 404)

    # 验证记录所属用户
    if not check_user_access(record["user_id"]):
        return APIResponse.error("无权修改", 403)

    data = request.get_json()
    fields = {}
    for k in ["mastery_level", "review_count", "is_mastered", "next_review_at"]:
        if k in data:
            fields[k] = data[k]

    if fields:
        records_crud.update(record_id, **fields)

    updated = records_crud.read(record_id)
    return APIResponse.success(updated, "更新学习记录成功")


@learning_bp.route("/record/<int:record_id>", methods=["DELETE"])
@handle_api_error
@require_auth
def delete_learning_record(record_id):
    """删除学习记录"""
    from tools.learning_records_crud import LearningRecordsCRUD

    records_crud = LearningRecordsCRUD()

    record = records_crud.read(record_id)
    if not record:
        return APIResponse.error("记录不存在", 404)

    # 验证记录所属用户
    if not check_user_access(record["user_id"]):
        return APIResponse.error("无权删除", 403)

    records_crud.delete(record_id)
    return APIResponse.success(None, "删除学习记录成功")


@learning_bp.route("/sessions/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_learning_sessions(user_id):
    """获取用户的学习会话列表"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    from tools.learning_sessions_crud import LearningSessionsCRUD

    sessions_crud = LearningSessionsCRUD()
    limit = request.args.get("limit", 50, type=int)
    offset = request.args.get("offset", 0, type=int)

    sessions = sessions_crud.get_by_user(user_id, limit, offset)
    return APIResponse.success(sessions, "获取学习会话列表成功")


@learning_bp.route("/session/<int:session_id>", methods=["DELETE"])
@handle_api_error
@require_auth
def delete_learning_session(session_id):
    """删除学习会话"""
    from tools.learning_sessions_crud import LearningSessionsCRUD

    sessions_crud = LearningSessionsCRUD()

    session = sessions_crud.get_by_id(session_id)
    if not session:
        return APIResponse.error("会话不存在", 404)

    # 验证会话所属用户
    if not check_user_access(session["user_id"]):
        return APIResponse.error("无权删除", 403)

    sessions_crud.delete(session_id)
    return APIResponse.success(None, "删除学习会话成功")
