"""
学习记录API模块
提供学习进度、统计、记录查询等功能接口
"""

from flask import Blueprint, request
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from core.learning.learning_record_manager import LearningRecordManager
from .utils import APIResponse, handle_api_error

# 创建蓝图
learning_bp = Blueprint('learning', __name__, url_prefix='/api/learning')

# 初始化管理器
vocabulary_manager = VocabularyLearningManager()
learning_record_manager = LearningRecordManager()

@learning_bp.route('/progress/<int:user_id>', methods=['GET'])
@handle_api_error
def get_learning_progress(user_id):
    """获取学习进度"""
    progress = vocabulary_manager.get_learning_progress(user_id)
    return APIResponse.success(progress, "获取学习进度成功")

@learning_bp.route('/statistics/<int:user_id>', methods=['GET'])
@handle_api_error
def get_learning_statistics(user_id):
    """获取学习统计"""
    days = request.args.get('days', 7, type=int)
    statistics = vocabulary_manager.get_learning_statistics(user_id, days)
    return APIResponse.success(statistics, "获取学习统计成功")

@learning_bp.route('/records/<int:user_id>', methods=['GET'])
@handle_api_error
def get_learning_records(user_id):
    """获取学习记录"""
    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)
    
    records = learning_record_manager.get_user_learning_records(user_id, limit, offset)
    return APIResponse.success(records, "获取学习记录成功")
