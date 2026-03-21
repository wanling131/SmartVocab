"""
评测模块API
"""

from flask import Blueprint, request
from core.evaluation.evaluation_manager import EvaluationManager
from tools.evaluation_results_crud import EvaluationResultsCRUD
from config import LEARNING_PARAMS
from .utils import APIResponse, handle_api_error

evaluation_bp = Blueprint('evaluation', __name__, url_prefix='/api/evaluation')
evaluation_manager = EvaluationManager()
results_crud = EvaluationResultsCRUD()


@evaluation_bp.route('/start', methods=['POST'])
@handle_api_error
def start_evaluation():
    """开始等级测试"""
    data = request.get_json()
    user_id = data.get('user_id')
    question_count = data.get('question_count', LEARNING_PARAMS.get("default_test_word_count", 10))
    difficulty_level = data.get('difficulty_level')
    dataset_type = data.get('dataset_type')
    
    if not user_id:
        return APIResponse.error('user_id 不能为空', 400)
    
    result = evaluation_manager.start_level_test(
        user_id=user_id,
        question_count=question_count,
        difficulty_level=difficulty_level,
        dataset_type=dataset_type
    )
    if result['success']:
        return APIResponse.success({
            'paper_id': result['paper_id'],
            'questions': result['questions'],
            'total_count': result['total_count']
        }, "开始测试成功")
    return APIResponse.error(result['message'], 400)


@evaluation_bp.route('/submit', methods=['POST'])
@handle_api_error
def submit_evaluation():
    """提交等级测试"""
    data = request.get_json()
    user_id = data.get('user_id')
    paper_id = data.get('paper_id')
    answers = data.get('answers', [])
    duration_seconds = data.get('duration_seconds', 0)
    
    if not user_id or not paper_id:
        return APIResponse.error('user_id 和 paper_id 不能为空', 400)
    
    result = evaluation_manager.submit_level_test(
        user_id=user_id,
        paper_id=paper_id,
        answers=answers,
        duration_seconds=duration_seconds
    )
    if result['success']:
        return APIResponse.success(result, "提交成功")
    return APIResponse.error(result['message'], 400)


@evaluation_bp.route('/history/<int:user_id>', methods=['GET'])
@handle_api_error
def get_history(user_id):
    """获取评测历史"""
    limit = request.args.get('limit', 50, type=int)
    history = results_crud.get_by_user(user_id, limit)
    return APIResponse.success(history, "获取评测历史成功")
