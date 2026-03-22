"""
词汇学习API模块
提供词汇学习、测试、练习、词库导入导出等功能接口
"""

import csv
import io
import json
from flask import Blueprint, request, jsonify, Response
from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from tools.words_crud import WordsCRUD
from config import LEARNING_PARAMS
from .utils import APIResponse, handle_api_error
from .auth_middleware import require_auth, get_current_user

# 创建蓝图
vocabulary_bp = Blueprint('vocabulary', __name__, url_prefix='/api/vocabulary')

# 初始化
vocabulary_manager = VocabularyLearningManager()
words_crud = WordsCRUD()


def _check_user_access(user_id) -> bool:
    """当前登录用户与请求中的 user_id 是否一致。"""
    current = get_current_user()
    if not current:
        return False
    try:
        return int(current.get('user_id')) == int(user_id)
    except (TypeError, ValueError):
        return False


def _session_info_matches_user(session_info) -> bool:
    """会话 JSON 中的 user_id 是否与当前登录用户一致。"""
    if not session_info or not isinstance(session_info, dict):
        return False
    return _check_user_access(session_info.get('user_id'))


@vocabulary_bp.route('/start-session', methods=['POST'])
@handle_api_error
@require_auth
def start_learning_session():
    """开始学习会话"""
    data = request.get_json()
    user_id = data.get('user_id')
    difficulty_level = data.get('difficulty_level')
    word_count = data.get('word_count', LEARNING_PARAMS["default_word_count"])
    question_type = data.get('question_type', 'mixed')
    
    if not user_id:
        return APIResponse.error('用户ID不能为空', 400)
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    result = vocabulary_manager.start_learning_session(user_id, difficulty_level, word_count, question_type)
    if result['success']:
        return APIResponse.success(result.get('session_info'), result['message'])
    else:
        return APIResponse.error(result['message'], 400)

@vocabulary_bp.route('/current-word', methods=['POST'])
@handle_api_error
@require_auth
def get_current_word():
    """获取当前学习的单词"""
    data = request.get_json()
    session_info = data.get('session_info')
    
    if not session_info:
        return APIResponse.error('会话信息不能为空', 400)
    if not _session_info_matches_user(session_info):
        return APIResponse.error('无权访问该会话', 403)

    word_info = vocabulary_manager.get_current_word(session_info)
    if word_info:
        return APIResponse.success(word_info, "获取单词成功")
    else:
        return APIResponse.error('没有更多单词', 404)

@vocabulary_bp.route('/submit-answer', methods=['POST'])
@handle_api_error
@require_auth
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
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    if session_info and not _session_info_matches_user(session_info):
        return APIResponse.error('无权访问该会话', 403)

    result = vocabulary_manager.submit_answer(
        user_id, word_id, user_answer, correct_answer, response_time, question_type, mastery_override, session_info
    )
    if result['success']:
        return APIResponse.success(result, result['message'])
    else:
        return APIResponse.error(result['message'], 400)

@vocabulary_bp.route('/active-session/<int:user_id>', methods=['GET'])
@handle_api_error
@require_auth
def get_active_session(user_id):
    """获取用户的活跃学习会话"""
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)
    session_type = request.args.get('session_type', 'learning')

    result = vocabulary_manager.get_active_session(user_id, session_type)
    if result['success']:
        return APIResponse.success(result['session_info'], result['message'])
    else:
        return APIResponse.error(result['message'], 404)

@vocabulary_bp.route('/finish-session', methods=['POST'])
@handle_api_error
@require_auth
def finish_session():
    """完成学习会话"""
    data = request.get_json()
    session_id = data.get('session_id')
    
    if not session_id:
        return APIResponse.error('会话ID不能为空', 400)
    try:
        sid = int(session_id)
    except (TypeError, ValueError):
        return APIResponse.error('会话ID无效', 400)

    row = vocabulary_manager.learning_sessions_crud.get_by_id(sid)
    if not row:
        return APIResponse.error('会话不存在', 404)
    if not _check_user_access(row.get('user_id')):
        return APIResponse.error('无权访问', 403)

    success = vocabulary_manager.finish_session(sid)
    if success:
        return APIResponse.success(None, "会话已完成")
    else:
        return APIResponse.error("完成会话失败", 400)

@vocabulary_bp.route('/start-review-session', methods=['POST'])
@handle_api_error
@require_auth
def start_review_session():
    data = request.get_json()
    user_id = data.get('user_id')
    word_count = data.get('word_count', LEARNING_PARAMS["default_word_count"])
    
    if not user_id:
        return APIResponse.error('用户ID不能为空', 400)
    if not _check_user_access(user_id):
        return APIResponse.error('无权访问', 403)

    result = vocabulary_manager.start_review_session(user_id, word_count)
    if result['success']:
        return APIResponse.success(result.get('session_info'), result['message'])
    else:
        return APIResponse.error(result['message'], 400)


@vocabulary_bp.route('/import', methods=['POST'])
@handle_api_error
@require_auth
def import_words():
    """批量导入词库（JSON body）"""
    data = request.get_json()
    if not data:
        return APIResponse.error('请提供 JSON 数据', 400)
    words_list = data if isinstance(data, list) else data.get('words', [])
    dataset_type = data.get('dataset_type') if isinstance(data, dict) else None
    count = 0
    for w in words_list:
        try:
            wid = words_crud.create(
                word=str(w.get('word', '')).strip(),
                translation=str(w.get('translation', '')).strip(),
                phonetic=w.get('phonetic', ''),
                pos=w.get('pos', ''),
                tag=w.get('tag', ''),
                total=int(w.get('frequency_rank', w.get('total', 0)) or 0),
                spoken_ratio=float(w.get('spoken_ratio', 0) or 0),
                academic_ratio=float(w.get('academic_ratio', 0) or 0),
                cefr_standard=w.get('cefr_standard', ''),
                difficulty_level=int(w.get('difficulty_level', 3) or 3),
                dataset_type=w.get('dataset_type') or dataset_type,
                definition_en=w.get('definition_en'),
                example_sentence=w.get('example_sentence')
            )
            if wid:
                count += 1
        except Exception:
            pass
    return APIResponse.success({'imported': count}, f"成功导入 {count} 个单词")


@vocabulary_bp.route('/export', methods=['GET'])
@handle_api_error
@require_auth
def export_words():
    """导出词库"""
    dataset_type = request.args.get('dataset_type')
    format_type = request.args.get('format', 'json')
    limit = request.args.get('limit', 10000, type=int)
    
    if dataset_type:
        words = words_crud.execute_query(
            "SELECT * FROM words WHERE dataset_type = %s LIMIT %s",
            (dataset_type, limit), fetch_all=True
        ) or []
    else:
        words = words_crud.list_all(limit=limit, offset=0)
    
    if format_type == 'csv':
        output = io.StringIO()
        writer = csv.writer(output)
        if words:
            writer.writerow(words[0].keys())
            for row in words:
                writer.writerow([str(v) if v is not None else '' for v in row.values()])
        return Response(output.getvalue(), mimetype='text/csv',
                       headers={'Content-Disposition': 'attachment;filename=words_export.csv'})
    return APIResponse.success(words, "导出成功")
