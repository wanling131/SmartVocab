"""
试卷题目表CRUD操作
"""

from typing import Any, Dict, List, Optional

from .base_crud import BaseCRUD


class EvaluationPaperItemsCRUD(BaseCRUD):
    """试卷题目表CRUD操作类"""

    def __init__(self):
        super().__init__("evaluation_paper_items")

    def create(
        self, paper_id: int, word_id: int, question_type: str, item_order: int
    ) -> Optional[int]:
        """
        创建试卷题目
        """
        query = """
        INSERT INTO evaluation_paper_items (paper_id, word_id, question_type, item_order)
        VALUES (%s, %s, %s, %s)
        """
        return self.execute_insert(query, (paper_id, word_id, question_type, item_order))

    def create_batch(self, paper_id: int, items: List[Dict[str, Any]]) -> int:
        """
        批量创建试卷题目
        items: [{"word_id": int, "question_type": str}, ...]
        """
        count = 0
        for i, item in enumerate(items):
            word_id = item.get("word_id")
            question_type = item.get("question_type", "choice")
            if word_id:
                pid = self.create(paper_id, word_id, question_type, i + 1)
                if pid:
                    count += 1
        return count

    def get_by_paper(self, paper_id: int) -> List[Dict[str, Any]]:
        """
        获取试卷所有题目（按 item_order 排序）
        """
        query = """
        SELECT epi.*, w.word, w.translation, w.phonetic, w.pos
        FROM evaluation_paper_items epi
        JOIN words w ON epi.word_id = w.id
        WHERE epi.paper_id = %s
        ORDER BY epi.item_order ASC
        """
        return self.execute_query(query, (paper_id,), fetch_one=False, fetch_all=True) or []
