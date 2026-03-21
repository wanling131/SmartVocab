"""
闯关模式API
"""

from flask import Blueprint, request
from tools.level_gates_crud import LevelGatesCRUD
from tools.user_level_progress_crud import UserLevelProgressCRUD
from tools.words_crud import WordsCRUD
from .utils import APIResponse, handle_api_error

levels_bp = Blueprint('levels', __name__, url_prefix='/api/levels')
gates_crud = LevelGatesCRUD()
progress_crud = UserLevelProgressCRUD()
words_crud = WordsCRUD()


@levels_bp.route('/gates', methods=['GET'])
@handle_api_error
def get_gates():
    """获取关卡列表"""
    gates = gates_crud.list_all()
    return APIResponse.success(gates, "获取关卡列表成功")


@levels_bp.route('/progress/<int:user_id>', methods=['GET'])
@handle_api_error
def get_progress(user_id):
    """获取用户关卡进度"""
    progress = progress_crud.get_by_user(user_id)
    return APIResponse.success(progress, "获取关卡进度成功")


@levels_bp.route('/unlock', methods=['POST'])
@handle_api_error
def unlock_gate():
    """解锁下一关（满足条件时）"""
    data = request.get_json()
    user_id = data.get('user_id')
    level_gate_id = data.get('level_gate_id')
    
    if not user_id or not level_gate_id:
        return APIResponse.error('user_id 和 level_gate_id 不能为空', 400)
    
    gate = gates_crud.read(level_gate_id)
    if not gate:
        return APIResponse.error('关卡不存在', 404)
    
    # 确保有进度记录
    progress = progress_crud.ensure_progress_exists(user_id, level_gate_id)
    if not progress:
        return APIResponse.error('创建进度失败', 500)
    
    # 检查上一关是否完成
    all_gates = gates_crud.list_all()
    prev_gate = next((g for g in all_gates if g['gate_order'] == gate['gate_order'] - 1), None)
    if prev_gate:
        prev_progress = progress_crud.get_by_user_gate(user_id, prev_gate['id'])
        if prev_progress and not prev_progress.get('is_completed'):
            return APIResponse.error('请先完成上一关', 400)
    
    success = progress_crud.unlock_gate(user_id, level_gate_id)
    if success:
        updated = progress_crud.get_by_user_gate(user_id, level_gate_id)
        return APIResponse.success(updated, "解锁成功")
    return APIResponse.error("解锁失败", 400)
