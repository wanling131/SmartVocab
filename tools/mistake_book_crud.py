"""
错题本 CRUD 操作
记录和管理用户的错误单词
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base_crud import BaseCRUD

logger = logging.getLogger(__name__)


class MistakeBookCRUD(BaseCRUD):
    """错题本 CRUD 操作类"""

    def __init__(self):
        super().__init__("mistake_book")

    def add_mistake(
        self,
        user_id: int,
        word_id: int,
        user_answer: str = None,
        correct_answer: str = None,
    ) -> Optional[int]:
        """
        添加或更新错题记录

        Args:
            user_id: 用户ID
            word_id: 单词ID
            user_answer: 用户错误答案
            correct_answer: 正确答案

        Returns:
            记录ID
        """
        # 检查是否已存在
        existing = self.get_by_user_and_word(user_id, word_id)

        if existing:
            # 更新错误次数
            query = """
                UPDATE mistake_book
                SET mistake_count = mistake_count + 1,
                    user_answer = %s,
                    last_mistake_at = %s
                WHERE id = %s
            """
            self.execute_update(
                query, (user_answer, datetime.now(), existing["id"])
            )
            return existing["id"]
        else:
            # 新增记录
            query = """
                INSERT INTO mistake_book
                (user_id, word_id, user_answer, correct_answer, first_mistake_at)
                VALUES (%s, %s, %s, %s, %s)
            """
            return self.execute_insert(
                query, (user_id, word_id, user_answer, correct_answer, datetime.now())
            )

    def get_by_user_and_word(self, user_id: int, word_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户特定单词的错题记录

        Args:
            user_id: 用户ID
            word_id: 单词ID

        Returns:
            错题记录或None
        """
        query = "SELECT * FROM mistake_book WHERE user_id = %s AND word_id = %s"
        return self.execute_query(query, (user_id, word_id), fetch_one=True)

    def get_user_mistakes(self, user_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """
        获取用户的错题列表

        Args:
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            错题记录列表
        """
        query = """
            SELECT mb.*, w.word, w.translation, w.phonetic, w.pos, w.example_sentence
            FROM mistake_book mb
            JOIN words w ON mb.word_id = w.id
            WHERE mb.user_id = %s AND mb.mastered = 0
            ORDER BY mb.mistake_count DESC, mb.last_mistake_at DESC
            LIMIT %s
        """
        return self.execute_query(query, (user_id, limit), fetch_all=True) or []

    def get_mistake_count(self, user_id: int) -> int:
        """
        获取用户错题总数

        Args:
            user_id: 用户ID

        Returns:
            错题数量
        """
        query = """
            SELECT COUNT(*) as count
            FROM mistake_book
            WHERE user_id = %s AND mastered = 0
        """
        result = self.execute_query(query, (user_id,), fetch_one=True)
        return result.get("count", 0) if result else 0

    def mark_mastered(self, user_id: int, word_id: int) -> int:
        """
        标记错题已掌握

        Args:
            user_id: 用户ID
            word_id: 单词ID

        Returns:
            受影响行数
        """
        query = """
            UPDATE mistake_book
            SET mastered = 1
            WHERE user_id = %s AND word_id = %s
        """
        return self.execute_update(query, (user_id, word_id))

    def get_mistake_words_for_review(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        获取用于复习的错题单词（带单词详情）

        Args:
            user_id: 用户ID
            limit: 返回数量限制

        Returns:
            单词列表（用于学习页）
        """
        mistakes = self.get_user_mistakes(user_id, limit)
        # 转换为学习页需要的格式
        words = []
        for m in mistakes:
            words.append({
                "id": m["word_id"],
                "word": m["word"],
                "translation": m["translation"],
                "phonetic": m["phonetic"],
                "pos": m["pos"],
                "example_sentence": m["example_sentence"],
                "mistake_count": m["mistake_count"],
                "user_answer": m["user_answer"],
                "correct_answer": m["correct_answer"],
            })
        return words


# 全局实例
mistake_book_crud = MistakeBookCRUD()