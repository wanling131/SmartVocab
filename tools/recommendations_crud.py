"""
推荐记录表CRUD操作（继承BaseCRUD）
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class RecommendationsCRUD(BaseCRUD):
    """推荐记录表CRUD操作类（继承BaseCRUD）"""

    def __init__(self):
        super().__init__("recommendations")

    def create(
        self,
        user_id: int,
        word_id: int,
        recommendation_score: float = 0.5,
        recommendation_type: str = "mixed",
        reason: str = None,
        created_at: datetime = None,
    ) -> Optional[int]:
        """
        创建推荐记录

        Args:
            user_id: 用户ID
            word_id: 单词ID
            recommendation_score: 推荐分数
            recommendation_type: 推荐算法类型
            reason: 推荐理由
            created_at: 创建时间

        Returns:
            新创建的记录ID
        """
        if created_at is None:
            created_at = datetime.now()

        query = """
        INSERT INTO recommendations (user_id, word_id, recommendation_score,
            recommendation_type, reason, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(
            query, (user_id, word_id, recommendation_score, recommendation_type, reason, created_at)
        )

    def get_by_user(self, user_id: int, limit: int = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取指定用户的推荐记录

        Args:
            user_id: 用户ID
            limit: 限制数量
            offset: 偏移量

        Returns:
            该用户的推荐记录列表
        """
        if limit:
            query = "SELECT * FROM recommendations WHERE user_id = %s LIMIT %s OFFSET %s"
            return self.execute_query(query, (user_id, limit, offset), fetch_all=True) or []
        else:
            query = "SELECT * FROM recommendations WHERE user_id = %s"
            return self.execute_query(query, (user_id,), fetch_all=True) or []

    def update(self, record_id: int, **kwargs) -> int:
        """
        更新推荐记录

        Args:
            record_id: 记录ID
            **kwargs: 要更新的字段

        Returns:
            受影响的行数
        """
        allowed_fields = ["recommendation_score", "recommendation_type", "reason"]
        query, params = self.build_update_query(kwargs, "id = %s", allowed_fields)
        if not query:
            return 0
        params = params + (record_id,)
        return self.execute_update(query, params)

    def get_user_recommendations(self, user_id: int) -> List[Dict[str, Any]]:
        """获取指定用户的推荐记录（兼容性方法）"""
        return self.get_by_user(user_id)
