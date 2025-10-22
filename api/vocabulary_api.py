"""
词汇学习API模块
提供词汇学习、测试、练习等核心功能接口
"""

from flask import Blueprint, request, jsonify
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from config import LEARNING_PARAMS
from .utils import APIResponse, handle_api_error

# 创建蓝图
vocabulary_bp = Blueprint('vocabulary', __name__, url_prefix='/api/vocabulary')

# 初始化词汇学习管理器
vocabulary_manager = VocabularyLearningManager()

@vocabulary_bp.route('/start-session', methods=['POST'])
@handle_api_error
def start_learning_session():
    """开始学习会话"""
    data = request.get_json()
    user_id = data.get('user_id')
    difficulty_level = data.get('difficulty_level')
    word_count = data.get('word_count', LEARNING_PARAMS["default_word_count"])
    question_type = data.get('question_type', 'mixed')
    
    if not user_id:
        return APIResponse.error('用户ID不能为空', 400)
    
    result = vocabulary_manager.start_learning_session(user_id, difficulty_level, word_count, question_type)
    if result['success']:
        return APIResponse.success(result.get('session_info'), result['message'])
    else:
        return APIResponse.error(result['message'], 400)

@vocabulary_bp.route('/current-word', methods=['POST'])
@handle_api_error
def get_current_word():
    """获取当前学习的单词"""
    data = request.get_json()
    session_info = data.get('session_info')
    
    if not session_info:
        return APIResponse.error('会话信息不能为空', 400)
    
    word_info = vocabulary_manager.get_current_word(session_info)
    if word_info:
        return APIResponse.success(word_info, "获取单词成功")
    else:
        return APIResponse.error('没有更多单词', 404)

@vocabulary_bp.route('/submit-answer', methods=['POST'])
@handle_api_error
def submit_answer():
    """提交答案"""
    data = request.get_json()
    user_id = data.get('user_id')
    word_id = data.get('word_id')
    user_answer = data.get('user_answer')
    correct_answer = data.get('correct_answer')
    response_time = data.get('response_time', 0)
    question_type = data.get('question_type', 'translation')
    mastery_override = data.get('mastery_override')
    session_info = data.get('session_info')
    
    if not all([user_id, word_id, user_answer, correct_answer]):
        return APIResponse.error('所有字段都不能为空', 400)
    
    result = vocabulary_manager.submit_answer(
        user_id, word_id, user_answer, correct_answer, response_time, question_type, mastery_override, session_info
    )
    if result['success']:
        return APIResponse.success(result, result['message'])
    else:
        return APIResponse.error(result['message'], 400)

@vocabulary_bp.route('/active-session/<int:user_id>', methods=['GET'])
@handle_api_error
def get_active_session(user_id):
    """获取用户的活跃学习会话"""
    session_type = request.args.get('session_type', 'learning')
    
    result = vocabulary_manager.get_active_session(user_id, session_type)
    if result['success']:
        return APIResponse.success(result['session_info'], result['message'])
    else:
        return APIResponse.error(result['message'], 404)

@vocabulary_bp.route('/finish-session', methods=['POST'])
@handle_api_error
def finish_session():
    """完成学习会话"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return APIResponse.error('会话ID不能为空', 400)
    
    success = vocabulary_manager.finish_session(session_id)
    if success:
        return APIResponse.success(None, "会话已完成")
    else:
        return APIResponse.error("完成会话失败", 400)

@vocabulary_bp.route('/start-review-session', methods=['POST'])
@handle_api_error
def start_review_session():
    data = request.get_json()
    user_id = data.get('user_id')
    word_count = data.get('word_count', LEARNING_PARAMS["default_word_count"])
    
    if not user_id:
        return APIResponse.error('用户ID不能为空', 400)
    
    result = vocabulary_manager.start_review_session(user_id, word_count)
    if result['success']:
        return APIResponse.success(result.get('session_info'), result['message'])
    else:
        return APIResponse.error(result['message'], 400)
