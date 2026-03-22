"""
学习记录API模块
提供学习进度、统计、记录查询等功能接口
"""

from flask import Blueprint, request
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from core.learning.learning_record_manager import LearningRecordManager
from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager
from config import LEARNING_PARAMS
from .utils import APIResponse, handle_api_error
from .auth_middleware import require_auth, get_current_user

# 创建蓝图
learning_bp = Blueprint('learning', __name__, url_prefix='/api/learning')

# 初始化管理器
vocabulary_manager = VocabularyLearningManager()
learning_record_manager = LearningRecordManager()
forgetting_curve_manager = ForgettingCurveManager()


def _check_user_access(user_id):
    """检查当前用户是否有权访问指定用户的数据"""
    current_user = get_current_user()
    if not current_user or current_user.get('user_id') != user_id:
        return False
    return True


@learning_bp.route('/progress/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_learning_progress(user_id):
    """获取学习进度"""
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    progress = vocabulary_manager.get_learning_progress(user_id)
    return APIResponse.success(progress, "获取学习进度成功")


@learning_bp.route('/statistics/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_learning_statistics(user_id):
    """获取学习统计"""
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    days = request.args.get('days', 7, type=int)
    statistics = vocabulary_manager.get_learning_statistics(user_id, days)
    return APIResponse.success(statistics, "获取学习统计成功")


@learning_bp.route('/records/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_learning_records(user_id):
    """获取学习记录"""
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)

    records = learning_record_manager.get_user_learning_records(user_id, limit, offset)
    return APIResponse.success(records, "获取学习记录成功")


@learning_bp.route('/forgetting-curve/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_forgetting_curve(user_id):
    """获取遗忘曲线数据（未来N天复习计划）"""
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    days = request.args.get('days', LEARNING_PARAMS.get("days_trend_analysis", 7), type=int)
    curve_data = forgetting_curve_manager.get_forgetting_curve_data(user_id, days)
    return APIResponse.success(curve_data, "获取遗忘曲线数据成功")
