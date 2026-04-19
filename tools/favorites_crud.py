"""
收藏单词 CRUD 操作
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class FavoritesCRUD(BaseCRUD):
    """用户收藏单词 CRUD"""

    def __init__(self):
        super().__init__("user_favorite_words")

    def add_favorite(self, user_id: int, word_id: int, note: str = None) -> Optional[int]:
        """添加收藏"""
        query = """
            INSERT INTO user_favorite_words (user_id, word_id, note, created_at)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE note = %s, updated_at = %s
        """
        now = datetime.now()
        return self.execute_insert(query, (user_id, word_id, note, now, note, now))

    def remove_favorite(self, user_id: int, word_id: int) -> bool:
        """取消收藏"""
        query = """
            DELETE FROM user_favorite_words
            WHERE user_id = %s AND word_id = %s
        """
        return self.execute_update(query, (user_id, word_id)) > 0

    def is_favorited(self, user_id: int, word_id: int) -> bool:
        """检查是否已收藏"""
        query = """
            SELECT COUNT(*) as cnt FROM user_favorite_words
            WHERE user_id = %s AND word_id = %s
        """
        result = self.execute_query(query, (user_id, word_id), fetch_one=True)
        return result.get("cnt", 0) > 0 if result else False

    def get_user_favorites(
        self, user_id: int, limit: int = 100, offset: int = 0
    ) -> List[Dict[str, Any]]:
        """获取用户收藏列表（含单词详情）"""
        query = """
            SELECT f.id, f.word_id, f.note, f.created_at as favorited_at,
                   w.word, w.translation, w.phonetic, w.pos,
                   w.difficulty_level, w.cefr_standard, w.dataset_type
            FROM user_favorite_words f
            JOIN words w ON f.word_id = w.id
            WHERE f.user_id = %s
            ORDER BY f.created_at DESC
            LIMIT %s OFFSET %s
        """
        results = self.execute_query(query, (user_id, limit, offset), fetch_all=True) or []
        for r in results:
            r.setdefault("dataset", r.get("dataset_type"))
        return results

    def get_favorite_count(self, user_id: int) -> int:
        """获取收藏数量"""
        query = "SELECT COUNT(*) as cnt FROM user_favorite_words WHERE user_id = %s"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return result.get("cnt", 0) if result else 0

    def get_favorited_word_ids(self, user_id: int) -> List[int]:
        """获取用户收藏的所有单词ID（用于前端快速判断）"""
        query = "SELECT word_id FROM user_favorite_words WHERE user_id = %s"
        results = self.execute_query(query, (user_id,), fetch_all=True) or []
        return [r["word_id"] for r in results]

    def update_note(self, user_id: int, word_id: int, note: str) -> bool:
        """更新收藏备注"""
        query = """
            UPDATE user_favorite_words
            SET note = %s, updated_at = %s
            WHERE user_id = %s AND word_id = %s
        """
        return self.execute_update(query, (note, datetime.now(), user_id, word_id)) > 0
