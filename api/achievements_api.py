"""
成就系统API
"""

import logging

from flask import Blueprint, request

from tools.achievements_crud import (
    AchievementService,
    LearningReportsCRUD,
    UserAchievementsCRUD,
    UserStreakCRUD,
)

from .auth_middleware import check_user_access, require_auth
from .utils import APIResponse, handle_api_error

logger = logging.getLogger(__name__)

achievements_bp = Blueprint("achievements", __name__, url_prefix="/api/achievements")
user_achievements_crud = UserAchievementsCRUD()
user_streak_crud = UserStreakCRUD()
reports_crud = LearningReportsCRUD()
achievement_service = AchievementService()


@achievements_bp.route("/<int:user_id>", methods=["GET"])
@handle_api_error
@require_auth
def get_user_achievements(user_id):
    """获取用户成就列表"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    achievements = user_achievements_crud.get_user_achievements(user_id)
    count = user_achievements_crud.get_achievement_count(user_id)
    streak = user_streak_crud.get_current_streak(user_id)

    return APIResponse.success(
        {"achievements": achievements, "total_count": count, "current_streak": streak},
        "获取成就成功",
    )


@achievements_bp.route("/<int:user_id>/streak", methods=["GET"])
@handle_api_error
@require_auth
def get_user_streak(user_id):
    """获取用户连续学习天数"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    streak = user_streak_crud.get_current_streak(user_id)
    return APIResponse.success({"streak": streak}, "获取连续学习天数成功")


@achievements_bp.route("/<int:user_id>/streak/update", methods=["POST"])
@handle_api_error
@require_auth
def update_user_streak(user_id):
    """更新连续学习记录"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    new_streak = user_streak_crud.update_streak(user_id)

    # 检查连续学习成就
    unlocked = achievement_service.check_streak(user_id, new_streak)

    # 检查时间成就
    time_achievement = achievement_service.check_time_achievement(user_id)
    if time_achievement:
        unlocked.append(time_achievement)

    return APIResponse.success(
        {"streak": new_streak, "new_achievements": unlocked}, f"连续学习 {new_streak} 天"
    )


@achievements_bp.route("/<int:user_id>/reports", methods=["GET"])
@handle_api_error
@require_auth
def get_user_reports(user_id):
    """获取用户学习报告列表"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    limit = request.args.get("limit", 10, type=int)
    reports = reports_crud.get_reports(user_id, limit)
    return APIResponse.success(reports, "获取报告列表成功")


@achievements_bp.route("/<int:user_id>/reports/weekly", methods=["GET"])
@handle_api_error
@require_auth
def get_weekly_report(user_id):
    """获取/生成周报告"""
    if not check_user_access(user_id):
        return APIResponse.error("无权访问", 403)

    from datetime import date, timedelta

    from tools.learning_records_crud import LearningRecordsCRUD

    end_date = date.today()
    start_date = end_date - timedelta(days=7)

    # 查询最近7天的学习数据（SQL 过滤，避免全量加载）
    records_crud = LearningRecordsCRUD()
    try:
        recent_records = records_crud.execute_query(
            "SELECT * FROM learning_records WHERE user_id = %s AND last_reviewed_at >= %s ORDER BY last_reviewed_at DESC",
            (user_id, start_date.isoformat()),
            fetch_all=True,
        ) or []
    except Exception:
        all_records = records_crud.get_by_user(user_id)
        recent_records = []
        for r in all_records:
            last_reviewed = r.get("last_reviewed_at")
            if last_reviewed:
                if isinstance(last_reviewed, str):
                    last_reviewed = date.fromisoformat(last_reviewed.split()[0])
                if start_date <= last_reviewed <= end_date:
                    recent_records.append(r)

    # 计算统计数据
    total_words = len(set(r["word_id"] for r in recent_records))
    total_reviews = sum(r.get("review_count", 0) for r in recent_records)
    total_mastered = sum(1 for r in recent_records if r.get("is_mastered"))
    avg_mastery = (
        sum(r.get("mastery_level", 0) for r in recent_records) / len(recent_records)
        if recent_records
        else 0
    )
    streak = user_streak_crud.get_current_streak(user_id)

    report = {
        "report_type": "weekly",
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "total_words_learned": total_words,
        "total_reviews": total_reviews,
        "total_mastered": total_mastered,
        "avg_mastery": round(avg_mastery, 2),
        "daily_streak": streak,
        "achievements_count": user_achievements_crud.get_achievement_count(user_id),
    }

    return APIResponse.success(report, "获取周报告成功")
