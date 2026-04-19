"""
学习记录表CRUD操作（继承BaseCRUD，带缓存优化）
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_crud import BaseCRUD
from .memory_cache import invalidate_user_cache, make_user_records_key, user_records_cache

logger = logging.getLogger(__name__)


class LearningRecordsCRUD(BaseCRUD):
    """学习记录表CRUD操作类（继承BaseCRUD，带缓存）"""

    def __init__(self):
        super().__init__("user_learning_records")

    def create(
        self,
        user_id: int,
        word_id: int,
        mastery_level: float = 0.0,
        last_reviewed_at: datetime = None,
        review_count: int = 0,
        is_mastered: bool = False,
        first_learned_at: datetime = None,
        next_review_at: datetime = None,
        level_gate_id: int = None,
    ) -> Optional[int]:
        """
        创建学习记录

        Args:
            user_id: 用户ID
            word_id: 单词ID
            mastery_level: 掌握程度
            last_reviewed_at: 最后复习时间
            review_count: 复习次数
            is_mastered: 是否已掌握
            first_learned_at: 首次学习时间
            next_review_at: 下次复习时间
            level_gate_id: 关卡ID

        Returns:
            新创建的记录ID
        """
        if last_reviewed_at is None:
            last_reviewed_at = datetime.now()
        if first_learned_at is None:
            first_learned_at = last_reviewed_at

        query = """
        INSERT INTO user_learning_records (user_id, word_id, level_gate_id,
            first_learned_at, last_reviewed_at, next_review_at,
            mastery_level, review_count, is_mastered)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (
            user_id,
            word_id,
            level_gate_id,
            first_learned_at,
            last_reviewed_at,
            next_review_at,
            mastery_level,
            review_count,
            is_mastered,
        )

        record_id = self.execute_insert(query, params)

        # 兼容旧版数据库（无 first_learned_at/next_review_at 列）
        if record_id is None:
            query = """
            INSERT INTO user_learning_records (user_id, word_id, last_reviewed_at,
                mastery_level, review_count, is_mastered)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            params = (user_id, word_id, last_reviewed_at, mastery_level, review_count, is_mastered)
            record_id = self.execute_insert(query, params)

        return record_id

    def get_by_user(self, user_id: int, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取指定用户的学习记录（带缓存）

        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            该用户的学习记录列表
        """
        # 缓存仅对有 limit 的查询
        if limit is not None:
            cache_key = make_user_records_key(user_id, limit, offset)
            cached = user_records_cache.get(cache_key)
            if cached is not None:
                return cached

        if limit:
            query = "SELECT * FROM user_learning_records WHERE user_id = %s ORDER BY last_reviewed_at DESC LIMIT %s OFFSET %s"
            results = self.execute_query(query, (user_id, limit, offset), fetch_all=True)
        else:
            query = "SELECT * FROM user_learning_records WHERE user_id = %s ORDER BY last_reviewed_at DESC"
            results = self.execute_query(query, (user_id,), fetch_all=True)

        # 缓存结果
        if limit is not None and results:
            user_records_cache.set(cache_key, results)

        return results or []

    def search_by_user_word(self, user_id: int, word_id: int) -> List[Dict[str, Any]]:
        """根据用户ID和单词ID搜索学习记录"""
        query = "SELECT * FROM user_learning_records WHERE user_id = %s AND word_id = %s"
        return self.execute_query(query, (user_id, word_id), fetch_all=True) or []

    def get_review_due(
        self, user_id: int, limit: int = 20, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        获取到期需复习的记录（next_review_at <= now）
        若表无 next_review_at 列则回退到 get_by_user
        """
        query = """
        SELECT * FROM user_learning_records
        WHERE user_id = %s AND (next_review_at IS NULL OR next_review_at <= NOW())
        ORDER BY COALESCE(next_review_at, '1970-01-01') ASC, last_reviewed_at ASC
        LIMIT %s OFFSET %s
        """
        try:
            return self.execute_query(query, (user_id, limit, offset), fetch_all=True) or []
        except Exception:
            # 回退到按 last_reviewed 获取
            return self.get_by_user(user_id, limit, offset)

    def read(self, record_id: int) -> Optional[Dict[str, Any]]:
        """根据ID读取学习记录"""
        query = "SELECT * FROM user_learning_records WHERE id = %s"
        return self.execute_query(query, (record_id,), fetch_one=True)

    def delete(self, record_id: int) -> int:
        """删除学习记录"""
        query = "DELETE FROM user_learning_records WHERE id = %s"
        return self.execute_update(query, (record_id,))

    def update(self, record_id: int, **kwargs) -> int:
        """
        更新学习记录（同时更新缓存）

        Args:
            record_id: 记录ID
            **kwargs: 要更新的字段

        Returns:
            受影响的行数
        """
        if not kwargs:
            return 0

        # 字段名映射（兼容旧 API）
        allowed_map = {
            "is_learned": "is_mastered",
            "last_reviewed": "last_reviewed_at",
            "mastery_level": "mastery_level",
            "review_count": "review_count",
            "is_mastered": "is_mastered",
            "last_reviewed_at": "last_reviewed_at",
            "first_learned_at": "first_learned_at",
            "next_review_at": "next_review_at",
            "level_gate_id": "level_gate_id",
        }

        fields = {}
        for field, value in kwargs.items():
            if field in allowed_map:
                fields[allowed_map[field]] = value

        if not fields:
            return 0

        query, params = self.build_update_query(fields, "id = %s", list(allowed_map.values()))
        params = params + (record_id,)
        affected_rows = self.execute_update(query, params)

        # 使缓存失效
        if affected_rows > 0:
            row = self.read(record_id)
            if row:
                invalidate_user_cache(row["user_id"])

        return affected_rows

    def get_user_records(self, user_id: int) -> List[Dict[str, Any]]:
        """获取指定用户的学习记录（兼容性方法）"""
        return self.get_by_user(user_id)

    def get_progress_stats(self, user_id: int) -> Dict[str, Any]:
        """
        SQL 聚合查询学习进度（避免全量加载）

        Returns:
            dict: {total_words, learned_words, learning_words, mastery_rate, total_reviews, average_mastery}
        """
        query = """
        SELECT
            COUNT(*) AS total_words,
            SUM(CASE WHEN is_mastered = 1 THEN 1 ELSE 0 END) AS learned_words,
            COALESCE(SUM(review_count), 0) AS total_reviews,
            COALESCE(AVG(mastery_level), 0) AS average_mastery
        FROM user_learning_records WHERE user_id = %s
        """
        row = self.execute_query(query, (user_id,), fetch_one=True)
        if not row:
            return {
                "total_words": 0, "learned_words": 0, "learning_words": 0,
                "mastery_rate": 0.0, "total_reviews": 0, "average_mastery": 0.0,
            }
        total = row["total_words"] or 0
        learned = row["learned_words"] or 0
        return {
            "total_words": total,
            "learned_words": learned,
            "learning_words": total - learned,
            "mastery_rate": round(learned / total, 2) if total > 0 else 0.0,
            "total_reviews": row["total_reviews"] or 0,
            "average_mastery": round(row["average_mastery"] or 0, 2),
        }

    def count_by_user(self, user_id: int) -> int:
        """获取用户学习记录总数（轻量 COUNT 查询）"""
        query = "SELECT COUNT(*) AS cnt FROM user_learning_records WHERE user_id = %s"
        row = self.execute_query(query, (user_id,), fetch_one=True)
        return row["cnt"] if row else 0

    def get_statistics_in_range(self, user_id: int, start_date, end_date) -> Dict[str, Any]:
        """
        SQL 聚合查询指定时间范围内的学习统计

        Args:
            user_id: 用户ID
            start_date: 起始日期 (datetime)
            end_date: 结束日期 (datetime)

        Returns:
            dict: {period_days, total_reviews, new_words, learned_words, active_days}
        """
        query = """
        SELECT
            COALESCE(SUM(review_count), 0) AS total_reviews,
            SUM(CASE WHEN review_count <= 1 THEN 1 ELSE 0 END) AS new_words,
            SUM(CASE WHEN is_mastered = 1 THEN 1 ELSE 0 END) AS learned_words,
            COUNT(DISTINCT DATE(last_reviewed_at)) AS active_days
        FROM user_learning_records
        WHERE user_id = %s AND last_reviewed_at >= %s AND last_reviewed_at <= %s
        """
        row = self.execute_query(query, (user_id, start_date, end_date), fetch_one=True)
        if not row:
            return {
                "period_days": (end_date - start_date).days,
                "total_reviews": 0, "new_words": 0,
                "learned_words": 0, "active_days": 0,
                "average_reviews_per_day": 0.0,
            }
        days = (end_date - start_date).days
        total_reviews = row["total_reviews"] or 0
        return {
            "period_days": days,
            "total_reviews": total_reviews,
            "new_words": row["new_words"] or 0,
            "learned_words": row["learned_words"] or 0,
            "active_days": row["active_days"] or 0,
            "average_reviews_per_day": round(total_reviews / days, 2) if days > 0 else 0.0,
        }

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取所有学习记录（用于推荐系统训练）

        Args:
            limit: 限制数量
            offset: 偏移量

        Returns:
            所有学习记录列表
        """
        query = "SELECT * FROM user_learning_records ORDER BY last_reviewed_at DESC LIMIT %s OFFSET %s"
        results = self.execute_query(query, (limit, offset), fetch_all=True)
        return results or []
