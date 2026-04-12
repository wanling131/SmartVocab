"""
闯关模式API
"""

import logging
from datetime import datetime

from flask import Blueprint, request

from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager
from tools.learning_records_crud import LearningRecordsCRUD
from tools.learning_sessions_crud import LearningSessionsCRUD
from tools.level_gates_crud import LevelGatesCRUD
from tools.user_level_progress_crud import UserLevelProgressCRUD
from tools.words_crud import WordsCRUD

from .auth_middleware import check_user_access, require_auth
from .utils import APIResponse, handle_api_error

logger = logging.getLogger(__name__)

levels_bp = Blueprint("levels", __name__, url_prefix="/api/levels")
gates_crud = LevelGatesCRUD()
progress_crud = UserLevelProgressCRUD()
words_crud = WordsCRUD()
learning_records_crud = LearningRecordsCRUD()
learning_sessions_crud = LearningSessionsCRUD()
vocabulary_manager = VocabularyLearningManager()


@levels_bp.route("/gates", methods=["GET"])
@handle_api_error
def get_gates():
    """获取关卡列表（公开）"""
    gates = gates_crud.list_all()
    return APIResponse.success(gates, "获取关卡列表成功")


@levels_bp.route("/gates/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_gates_with_progress(user_id):
    """获取关卡列表（含用户进度）"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    gates = gates_crud.list_all() or []
    progress = progress_crud.get_by_user(user_id) or []
    # 使用 level_gate_id 字段（数据库列名）
    progress_map = {p["level_gate_id"]: p for p in progress}
    result = []
    for gate in gates:
        p = progress_map.get(gate["id"], {})
        # 使用 gate_order 字段（数据库列名）
        is_first_gate = gate.get("gate_order", 1) == 1 or gate.get("order_index", 1) == 1
        result.append(
            {
                **gate,
                "is_unlocked": p.get("is_unlocked", is_first_gate),
                "is_completed": p.get("is_completed", False),
                "user_score": p.get("best_score"),
                # 添加前端期望的字段名（兼容）
                "order": gate.get("gate_order"),
                "name": gate.get("gate_name"),
                "description": gate.get("description", f"难度 {gate.get('difficulty_level', 1)} 关卡"),
            }
        )
    return APIResponse.success(result, "获取关卡列表成功")


@levels_bp.route("/progress/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_progress(user_id):
    """获取用户关卡进度"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    progress = progress_crud.get_by_user(user_id)
    return APIResponse.success(progress, "获取关卡进度成功")


@levels_bp.route("/unlock", methods=["POST"])
@handle_api_error
@require_auth
def unlock_gate():
    """解锁下一关（满足条件时）"""
    data = request.get_json()
    user_id = data.get("user_id")
    level_gate_id = data.get("level_gate_id") or data.get("gate_id")

    if not user_id or not level_gate_id:
        return APIResponse.error("user_id 和 level_gate_id 不能为空", 400)

    # 验证用户身份
    if not check_user_access(user_id):
        return APIResponse.error("无权操作", 403)

    gate = gates_crud.read(level_gate_id)
    if not gate:
        return APIResponse.error("关卡不存在", 404)

    # 确保有进度记录
    progress = progress_crud.ensure_progress_exists(user_id, level_gate_id)
    if not progress:
        return APIResponse.error("创建进度失败", 500)

    # 检查上一关是否完成
    all_gates = gates_crud.list_all()
    prev_gate = next((g for g in all_gates if g["gate_order"] == gate["gate_order"] - 1), None)
    if prev_gate:
        prev_progress = progress_crud.get_by_user_gate(user_id, prev_gate["id"])
        if prev_progress and not prev_progress.get("is_completed"):
            return APIResponse.error("请先完成上一关", 400)

    success = progress_crud.unlock_gate(user_id, level_gate_id)
    if success:
        updated = progress_crud.get_by_user_gate(user_id, level_gate_id)
        return APIResponse.success(updated, "解锁成功")
    return APIResponse.error("解锁失败", 400)


@levels_bp.route("/start/<int:gate_id>", methods=["POST"])
@handle_api_error
@require_auth
def start_gate_session(gate_id):
    """开始闯关学习会话"""
    data = request.get_json()
    user_id = data.get("user_id")

    if not user_id:
        return APIResponse.error("user_id 不能为空", 400)

    # 验证用户身份
    if not check_user_access(user_id):
        return APIResponse.error("无权操作", 403)

    # 获取关卡信息
    gate = gates_crud.read(gate_id)
    if not gate:
        return APIResponse.error("关卡不存在", 404)

    # 检查关卡是否已解锁
    progress = progress_crud.get_by_user_gate(user_id, gate_id)
    if not progress:
        # 自动创建并解锁第一关
        if gate["gate_order"] == 1:
            progress = progress_crud.ensure_progress_exists(user_id, gate_id)
            progress_crud.unlock_gate(user_id, gate_id)
        else:
            return APIResponse.error("该关卡尚未解锁", 403)

    if not progress.get("is_unlocked"):
        return APIResponse.error("该关卡尚未解锁", 403)

    # 获取关卡难度的单词
    difficulty = gate.get("difficulty_level", 1)
    word_count = gate.get("word_count", 20)

    # 获取用户已学习的单词
    learned_records = learning_records_crud.get_by_user(user_id)
    learned_word_ids = {r["word_id"] for r in learned_records}

    # 获取该难度的单词（排除已学习的）
    all_words = words_crud.get_by_difficulty(difficulty)
    available_words = [w for w in all_words if w["id"] not in learned_word_ids]

    if len(available_words) < word_count:
        # 如果单词不够，从已学习的该难度单词中选择
        reviewed_words = [w for w in all_words if w["id"] in learned_word_ids]
        available_words = available_words + reviewed_words

    if not available_words:
        return APIResponse.error("该难度暂无可用单词", 400)

    import random

    selected_words = random.sample(available_words, min(word_count, len(available_words)))

    # 创建学习会话
    session_info = {
        "user_id": user_id,
        "words": selected_words,
        "current_word_index": 0,
        "correct_count": 0,
        "total_count": len(selected_words),
        "start_time": datetime.now(),
        "session_type": "gate",
        "gate_id": gate_id,
        "difficulty_level": difficulty,
        "question_type": "mixed",
        "word_stages": {},
    }

    session_id = learning_sessions_crud.create(user_id, session_info, "gate")
    if session_id:
        session_info["session_id"] = session_id

    gate_name = gate.get("gate_name") or f"第{gate.get('gate_order', 1)}关"
    return APIResponse.success(
        {"session_info": session_info, "gate": gate}, f"开始闯关：{gate_name}"
    )


@levels_bp.route("/complete/<int:gate_id>", methods=["POST"])
@handle_api_error
@require_auth
def complete_gate(gate_id):
    """完成关卡并更新进度"""
    data = request.get_json()
    user_id = data.get("user_id")
    correct_count = data.get("correct_count", 0)
    total_count = data.get("total_count", 1)

    if not user_id:
        return APIResponse.error("user_id 不能为空", 400)

    # 验证用户身份
    if not check_user_access(user_id):
        return APIResponse.error("无权操作", 403)

    # 计算正确率
    accuracy = correct_count / total_count if total_count > 0 else 0

    # 获取关卡信息
    gate = gates_crud.read(gate_id)
    if not gate:
        return APIResponse.error("关卡不存在", 404)

    # 获取当前进度
    progress = progress_crud.get_by_user_gate(user_id, gate_id)
    if not progress:
        progress = progress_crud.ensure_progress_exists(user_id, gate_id)

    # 更新掌握数量
    mastered_count = progress.get("mastered_count", 0) + correct_count
    is_completed = accuracy >= 0.8  # 正确率80%以上视为通关

    # 更新进度
    progress_crud.update_progress_by_user_gate(user_id, gate_id, mastered_count, is_completed)

    # 如果通关，解锁下一关
    next_gate = None
    if is_completed:
        all_gates = gates_crud.list_all()
        next_gate = next((g for g in all_gates if g["gate_order"] == gate["gate_order"] + 1), None)
        if next_gate:
            progress_crud.ensure_progress_exists(user_id, next_gate["id"])
            progress_crud.unlock_gate(user_id, next_gate["id"])

    return APIResponse.success(
        {
            "accuracy": accuracy,
            "is_completed": is_completed,
            "mastered_count": mastered_count,
            "next_gate": next_gate,
        },
        "通关成功！" if is_completed else "继续努力！",
    )
