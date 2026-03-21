"""
学习计划API模块
"""

from flask import Blueprint, request
from tools.user_learning_plans_crud import UserLearningPlansCRUD
from .utils import APIResponse, handle_api_error

plans_bp = Blueprint('plans', __name__, url_prefix='/api/plans')
plans_crud = UserLearningPlansCRUD()


@plans_bp.route('/<int:user_id>', methods=['GET'])
@handle_api_error
def get_plans(user_id):
    """获取用户计划列表"""
    limit = request.args.get('limit', 50, type=int)
    plans = plans_crud.get_by_user(user_id, limit)
    return APIResponse.success(plans, "获取计划列表成功")


@plans_bp.route('/<int:user_id>/active', methods=['GET'])
@handle_api_error
def get_active_plan(user_id):
    """获取用户当前生效计划"""
    plan = plans_crud.get_active_plan(user_id)
    return APIResponse.success(plan, "获取生效计划成功")


@plans_bp.route('', methods=['POST'])
@handle_api_error
def create_plan():
    """创建学习计划"""
    data = request.get_json()
    user_id = data.get('user_id')
    dataset_type = data.get('dataset_type')
    daily_new_count = data.get('daily_new_count', 20)
    daily_review_count = data.get('daily_review_count', 20)
    plan_name = data.get('plan_name')
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not user_id or not dataset_type:
        return APIResponse.error('user_id 和 dataset_type 不能为空', 400)
    
    # 将新计划设为生效前，先停用其他计划
    active = plans_crud.get_active_plan(user_id)
    if active:
        plans_crud.deactivate(active['id'])
    
    plan_id = plans_crud.create(
        user_id=user_id,
        dataset_type=dataset_type,
        daily_new_count=daily_new_count,
        daily_review_count=daily_review_count,
        plan_name=plan_name,
        start_date=start_date,
        end_date=end_date,
        is_active=True
    )
    if plan_id:
        plan = plans_crud.read(plan_id)
        return APIResponse.success(plan, "创建计划成功")
    return APIResponse.error("创建计划失败", 400)


@plans_bp.route('/<int:plan_id>', methods=['PUT'])
@handle_api_error
def update_plan(plan_id):
    """更新学习计划"""
    data = request.get_json()
    plan = plans_crud.read(plan_id)
    if not plan:
        return APIResponse.error("计划不存在", 404)
    
    fields = {}
    for k in ['plan_name', 'dataset_type', 'daily_new_count', 'daily_review_count', 'start_date', 'end_date', 'is_active']:
        if k in data:
            fields[k] = data[k]
    
    if fields:
        plans_crud.update(plan_id, **fields)
    updated = plans_crud.read(plan_id)
    return APIResponse.success(updated, "更新计划成功")


@plans_bp.route('/<int:plan_id>', methods=['DELETE'])
@handle_api_error
def delete_plan(plan_id):
    """删除/停用学习计划"""
    plan = plans_crud.read(plan_id)
    if not plan:
        return APIResponse.error("计划不存在", 404)
    plans_crud.deactivate(plan_id)
    return APIResponse.success(None, "计划已停用")
