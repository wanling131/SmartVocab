"""
学习计划API模块
"""

import logging

from flask import Blueprint, request

from tools.user_learning_plans_crud import UserLearningPlansCRUD
from tools.words_crud import WordsCRUD

from .auth_middleware import check_user_access, require_auth
from .utils import APIResponse, handle_api_error

logger = logging.getLogger(__name__)

plans_bp = Blueprint("plans", __name__, url_prefix="/api/plans")
plans_crud = UserLearningPlansCRUD()
words_crud = WordsCRUD()


def _add_plan_aliases(plan):
    """为计划数据添加前端期望的字段别名"""
    if not plan:
        return plan
    plan.setdefault("name", plan.get("plan_name"))
    plan.setdefault("dataset", plan.get("dataset_type"))
    plan.setdefault("daily_new_words", plan.get("daily_new_count"))
    plan.setdefault("daily_review_words", plan.get("daily_review_count"))
    return plan


@plans_bp.route("/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_plans(user_id):
    """获取用户计划列表"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    limit = request.args.get("limit", 50, type=int)
    plans = plans_crud.get_by_user(user_id, limit)
    return APIResponse.success([_add_plan_aliases(p) for p in plans], "获取计划列表成功")


@plans_bp.route("", methods=["GET"])
@handle_api_error
@require_auth
def get_plans_by_query():
    """通过 query param 获取用户计划列表（兼容前端调用）"""
    user_id = request.args.get("user_id", type=int)
    if not user_id:
        return APIResponse.error("user_id 参数不能为空", 400)
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    limit = request.args.get("limit", 50, type=int)
    plans = plans_crud.get_by_user(user_id, limit)
    return APIResponse.success([_add_plan_aliases(p) for p in plans], "获取计划列表成功")


@plans_bp.route("/<int:user_id>/active", methods=["GET"])
@handle_api_error
@require_auth
def get_active_plan(user_id):
    """获取用户当前生效计划"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)
    plan = plans_crud.get_active_plan(user_id)
    return APIResponse.success(_add_plan_aliases(plan), "获取生效计划成功")


@plans_bp.route("", methods=["POST"])
@handle_api_error
@require_auth
def create_plan():
    """创建学习计划"""
    data = request.get_json()
    user_id = data.get("user_id")
    dataset_type = data.get("dataset_type") or data.get("dataset")
    daily_new_count = data.get("daily_new_count") or data.get("daily_new_words", 20)
    daily_review_count = data.get("daily_review_count") or data.get("daily_review_words", 20)
    plan_name = data.get("plan_name") or data.get("name")
    start_date = data.get("start_date")
    end_date = data.get("end_date")

    if not user_id or not dataset_type:
        return APIResponse.error("user_id 和 dataset_type 不能为空", 400)

    # 验证用户身份
    if not check_user_access(user_id):
        return APIResponse.error("无权创建计划", 403)

    # 将新计划设为生效前，先停用其他计划
    active = plans_crud.get_active_plan(user_id)
    if active:
        plans_crud.deactivate(active["id"])

    plan_id = plans_crud.create(
        user_id=user_id,
        dataset_type=dataset_type,
        daily_new_count=daily_new_count,
        daily_review_count=daily_review_count,
        plan_name=plan_name,
        start_date=start_date,
        end_date=end_date,
        is_active=True,
    )
    if plan_id:
        plan = plans_crud.read(plan_id)
        return APIResponse.success(plan, "创建计划成功")
    return APIResponse.error("创建计划失败", 400)


@plans_bp.route("/<int:plan_id>", methods=["PUT"])
@handle_api_error
@require_auth
def update_plan(plan_id):
    """更新学习计划"""
    plan = plans_crud.read(plan_id)
    if not plan:
        return APIResponse.error("计划不存在", 404)

    # 验证计划所属用户
    if not check_user_access(plan["user_id"]):
        return APIResponse.error("无权修改此计划", 403)

    data = request.get_json()
    fields = {}
    for k in [
        "plan_name",
        "dataset_type",
        "daily_new_count",
        "daily_review_count",
        "start_date",
        "end_date",
        "is_active",
    ]:
        if k in data:
            fields[k] = data[k]

    if fields:
        plans_crud.update(plan_id, **fields)
    updated = plans_crud.read(plan_id)
    return APIResponse.success(updated, "更新计划成功")


@plans_bp.route("/<int:plan_id>", methods=["DELETE"])
@handle_api_error
@require_auth
def delete_plan(plan_id):
    """删除/停用学习计划"""
    plan = plans_crud.read(plan_id)
    if not plan:
        return APIResponse.error("计划不存在", 404)

    # 验证计划所属用户
    if not check_user_access(plan["user_id"]):
        return APIResponse.error("无权删除此计划", 403)

    plans_crud.deactivate(plan_id)
    return APIResponse.success(None, "计划已停用")


@plans_bp.route("/<int:plan_id>/deactivate", methods=["POST"])
@handle_api_error
@require_auth
def deactivate_plan(plan_id):
    """停用计划"""
    plan = plans_crud.read(plan_id)
    if not plan:
        return APIResponse.error("计划不存在", 404)
    if not check_user_access(plan["user_id"]):
        return APIResponse.error("无权操作", 403)
    plans_crud.deactivate(plan_id)
    return APIResponse.success(None, "计划已停用")


@plans_bp.route("/<int:plan_id>/activate", methods=["POST"])
@handle_api_error
@require_auth
def activate_plan(plan_id):
    """激活计划"""
    plan = plans_crud.read(plan_id)
    if not plan:
        return APIResponse.error("计划不存在", 404)
    if not check_user_access(plan["user_id"]):
        return APIResponse.error("无权操作", 403)
    # 先停用当前生效的计划
    active = plans_crud.get_active_plan(plan["user_id"])
    if active:
        plans_crud.deactivate(active["id"])
    plans_crud.update(plan_id, is_active=True)
    return APIResponse.success(None, "计划已激活")


@plans_bp.route("/<int:user_id>/start-learning", methods=["POST"])
@handle_api_error
@require_auth
def start_plan_learning(user_id):
    """根据用户生效计划开始学习"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    # 获取用户生效计划
    plan = plans_crud.get_active_plan(user_id)
    if not plan:
        return APIResponse.error("请先创建学习计划", 400)

    dataset_type = plan.get("dataset_type")
    daily_new_count = plan.get("daily_new_count", 20)

    # 根据计划词库类型获取单词
    words = words_crud.get_by_dataset_type(dataset_type, limit=daily_new_count * 2)

    if not words:
        return APIResponse.error("该词库暂无可用单词", 400)

    # 排除已学习的单词
    from tools.learning_records_crud import LearningRecordsCRUD

    records_crud = LearningRecordsCRUD()
    learned_records = records_crud.get_by_user(user_id)
    learned_word_ids = {r["word_id"] for r in learned_records}

    available_words = [w for w in words if w["id"] not in learned_word_ids]

    if not available_words:
        # 如果没有新词，使用已学习的单词进行复习
        available_words = words[:daily_new_count]

    import random

    selected_words = random.sample(available_words, min(daily_new_count, len(available_words)))

    return APIResponse.success(
        {
            "plan": plan,
            "words": selected_words,
            "total_count": len(selected_words),
            "dataset_type": dataset_type,
        },
        f"开始学习 {dataset_type.upper()} 词库",
    )
