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
