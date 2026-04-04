"""
成就系统CRUD操作
"""

import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from .base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class UserAchievementsCRUD(BaseCRUD):
    """用户成就记录CRUD"""

    def __init__(self):
        super().__init__("user_achievements")

    def get_user_achievements(self, user_id: int) -> List[Dict[str, Any]]:
        """获取用户所有成就"""
        query = """
            SELECT * FROM user_achievements
            WHERE user_id = %s
            ORDER BY earned_at DESC
        """
        return self.execute_query(query, (user_id,), fetch_all=True) or []

    def has_achievement(self, user_id: int, achievement_type: str) -> bool:
        """检查用户是否已有某成就"""
        query = """
            SELECT COUNT(*) as cnt FROM user_achievements
            WHERE user_id = %s AND achievement_type = %s
        """
        result = self.execute_query(query, (user_id, achievement_type), fetch_one=True)
        return result.get('cnt', 0) > 0 if result else False

    def unlock_achievement(self, user_id: int, achievement_type: str,
                          achievement_name: str, description: str = None,
                          icon: str = '🏆', threshold: int = 1) -> Optional[int]:
        """解锁成就"""
        if self.has_achievement(user_id, achievement_type):
            return None

        query = """
            INSERT INTO user_achievements
            (user_id, achievement_type, achievement_name, achievement_description, icon, threshold, earned_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (
            user_id, achievement_type, achievement_name, description, icon, threshold, datetime.now()
        ))

    def get_achievement_count(self, user_id: int) -> int:
        """获取用户成就数量"""
        query = "SELECT COUNT(*) as cnt FROM user_achievements WHERE user_id = %s"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return result.get('cnt', 0) if result else 0


class UserStreakCRUD(BaseCRUD):
    """连续学习记录CRUD"""

    def __init__(self):
        super().__init__("user_streak")

    def get_current_streak(self, user_id: int) -> int:
        """获取当前连续学习天数"""
        today = date.today()
        query = """
            SELECT streak_count, last_study_date FROM user_streak
            WHERE user_id = %s
            ORDER BY last_study_date DESC
            LIMIT 1
        """
        result = self.execute_query(query, (user_id,), fetch_one=True)

        if not result:
            return 0

        last_date = result.get('last_study_date')
        if isinstance(last_date, str):
            last_date = date.fromisoformat(last_date)

        days_diff = (today - last_date).days
        if days_diff > 1:
            # 连续中断
            return 0
        return result.get('streak_count', 0)

    def update_streak(self, user_id: int) -> int:
        """更新连续学习记录，返回新的连续天数"""
        today = date.today()

        # 查找最近的记录
        query = """
            SELECT id, streak_count, last_study_date, start_date FROM user_streak
            WHERE user_id = %s
            ORDER BY last_study_date DESC
            LIMIT 1
        """
        result = self.execute_query(query, (user_id,), fetch_one=True)

        if not result:
            # 首次学习
            insert_query = """
                INSERT INTO user_streak (user_id, streak_count, last_study_date, start_date)
                VALUES (%s, 1, %s, %s)
            """
            self.execute_insert(insert_query, (user_id, today, today))
            return 1

        last_date = result.get('last_study_date')
        if isinstance(last_date, str):
            last_date = date.fromisoformat(last_date)

        days_diff = (today - last_date).days

        if days_diff == 0:
            # 今天已更新
            return result.get('streak_count', 0)
        elif days_diff == 1:
            # 连续学习
            new_count = result.get('streak_count', 0) + 1
            update_query = """
                UPDATE user_streak
                SET streak_count = %s, last_study_date = %s, updated_at = %s
                WHERE id = %s
            """
            self.execute_update(update_query, (new_count, today, datetime.now(), result['id']))
            return new_count
        else:
            # 连续中断，重新开始
            insert_query = """
                INSERT INTO user_streak (user_id, streak_count, last_study_date, start_date)
                VALUES (%s, 1, %s, %s)
            """
            self.execute_insert(insert_query, (user_id, today, today))
            return 1


class LearningReportsCRUD(BaseCRUD):
    """学习报告CRUD"""

    def __init__(self):
        super().__init__("learning_reports")

    def get_latest_report(self, user_id: int, report_type: str) -> Optional[Dict[str, Any]]:
        """获取最新报告"""
        query = """
            SELECT * FROM learning_reports
            WHERE user_id = %s AND report_type = %s
            ORDER BY report_end_date DESC
            LIMIT 1
        """
        return self.execute_query(query, (user_id, report_type), fetch_one=True)

    def get_reports(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """获取用户报告列表"""
        query = """
            SELECT * FROM learning_reports
            WHERE user_id = %s
            ORDER BY report_end_date DESC
            LIMIT %s
        """
        return self.execute_query(query, (user_id, limit), fetch_all=True) or []

    def create_report(self, user_id: int, report_type: str, start_date: date, end_date: date,
                     total_words: int = 0, total_reviews: int = 0, total_mastered: int = 0,
                     avg_accuracy: float = 0.0, total_time: int = 0, streak: int = 0,
                     achievements: list = None, report_data: dict = None) -> Optional[int]:
        """创建学习报告"""
        import json
        query = """
            INSERT INTO learning_reports
            (user_id, report_type, report_start_date, report_end_date,
             total_words_learned, total_reviews, total_mastered, avg_accuracy,
             total_time_minutes, daily_streak, achievements, report_data)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (
            user_id, report_type, start_date, end_date,
            total_words, total_reviews, total_mastered, avg_accuracy,
            total_time, streak,
            json.dumps(achievements, ensure_ascii=False) if achievements else None,
            json.dumps(report_data, ensure_ascii=False) if report_data else None
        ))


class AchievementService:
    """成就服务 - 检查和解锁成就"""

    # 成就定义
    ACHIEVEMENTS = {
        # 学习数量成就
        'first_blood': {'name': '初学者', 'desc': '学习第一个单词', 'icon': '🌱'},
        'words_10': {'name': '起步者', 'desc': '学习10个单词', 'icon': '🌿'},
        'words_50': {'name': '入门者', 'desc': '学习50个单词', 'icon': '🌳'},
        'words_100': {'name': '进阶者', 'desc': '学习100个单词', 'icon': '🌲'},
        'words_500': {'name': '达人', 'desc': '学习500个单词', 'icon': '🏆'},
        'words_1000': {'name': '词汇大师', 'desc': '学习1000个单词', 'icon': '👑'},

        # 连续学习成就
        'streak_3': {'name': '坚持3天', 'desc': '连续学习3天', 'icon': '🔥'},
        'streak_7': {'name': '坚持一周', 'desc': '连续学习7天', 'icon': '🔥'},
        'streak_30': {'name': '坚持一月', 'desc': '连续学习30天', 'icon': '💪'},
        'streak_100': {'name': '百日坚持', 'desc': '连续学习100天', 'icon': '⭐'},

        # 正确率成就
        'accuracy_80': {'name': '精准学习者', 'desc': '单次正确率达80%', 'icon': '🎯'},
        'accuracy_90': {'name': '高准确率', 'desc': '单次正确率达90%', 'icon': '🎯'},
        'perfect_score': {'name': '完美表现', 'desc': '单次正确率达100%', 'icon': '💯'},

        # 特殊成就
        'first_review': {'name': '温故知新', 'desc': '完成第一次复习', 'icon': '📖'},
        'first_test': {'name': '初试锋芒', 'desc': '完成第一次测试', 'icon': '📝'},
        'first_plan': {'name': '规划者', 'desc': '创建第一个学习计划', 'icon': '📅'},
        'level_complete': {'name': '闯关达人', 'desc': '完成一个关卡', 'icon': '🚩'},
        'night_owl': {'name': '夜猫子', 'desc': '在深夜学习', 'icon': '🦉'},
        'early_bird': {'name': '早起鸟', 'desc': '在早晨学习', 'icon': '🐦'},
    }

    def __init__(self):
        self.crud = UserAchievementsCRUD()

    def unlock(self, user_id: int, achievement_type: str) -> Optional[Dict[str, Any]]:
        """解锁成就"""
        if achievement_type not in self.ACHIEVEMENTS:
            return None

        achievement = self.ACHIEVEMENTS[achievement_type]
        record_id = self.crud.unlock_achievement(
            user_id=user_id,
            achievement_type=achievement_type,
            achievement_name=achievement['name'],
            description=achievement['desc'],
            icon=achievement['icon']
        )

        if record_id:
            logger.info("用户 %s 解锁成就: %s", user_id, achievement_type)
            return {'type': achievement_type, **achievement}
        return None

    def check_word_count(self, user_id: int, total_words: int) -> List[Dict[str, Any]]:
        """检查学习数量成就"""
        unlocked = []
        thresholds = [(1, 'first_blood'), (10, 'words_10'), (50, 'words_50'),
                      (100, 'words_100'), (500, 'words_500'), (1000, 'words_1000')]

        for threshold, key in thresholds:
            if total_words >= threshold:
                result = self.unlock(user_id, key)
                if result:
                    unlocked.append(result)
        return unlocked

    def check_streak(self, user_id: int, streak_days: int) -> List[Dict[str, Any]]:
        """检查连续学习成就"""
        unlocked = []
        thresholds = [(3, 'streak_3'), (7, 'streak_7'), (30, 'streak_30'), (100, 'streak_100')]

        for threshold, key in thresholds:
            if streak_days >= threshold:
                result = self.unlock(user_id, key)
                if result:
                    unlocked.append(result)
        return unlocked

    def check_accuracy(self, user_id: int, accuracy: float) -> List[Dict[str, Any]]:
        """检查正确率成就"""
        unlocked = []

        if accuracy >= 100:
            result = self.unlock(user_id, 'perfect_score')
            if result:
                unlocked.append(result)
        if accuracy >= 90:
            result = self.unlock(user_id, 'accuracy_90')
            if result:
                unlocked.append(result)
        if accuracy >= 80:
            result = self.unlock(user_id, 'accuracy_80')
            if result:
                unlocked.append(result)
        return unlocked

    def check_time_achievement(self, user_id: int) -> Optional[Dict[str, Any]]:
        """检查时间成就"""
        hour = datetime.now().hour
        if 23 <= hour or hour < 5:
            return self.unlock(user_id, 'night_owl')
        elif 5 <= hour < 7:
            return self.unlock(user_id, 'early_bird')
        return None
