"""
评测试卷表CRUD操作
"""

from .base_crud import BaseCRUD
from typing import Optional, List, Dict, Any
from datetime import datetime


class EvaluationPapersCRUD(BaseCRUD):
    """评测试卷表CRUD操作类"""
    
    def __init__(self):
        super().__init__("evaluation_papers")
    
    def create(self, user_id: int, paper_type: str, question_count: int) -> Optional[int]:
        """
        创建试卷
        """
        self.log_operation("创建试卷", user_id=user_id, paper_type=paper_type)
        query = """
        INSERT INTO evaluation_papers (user_id, paper_type, question_count)
        VALUES (%s, %s, %s)
        """
        return self.execute_insert(query, (user_id, paper_type, question_count))
    
    def read(self, paper_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取试卷
        """
        query = "SELECT * FROM evaluation_papers WHERE id = %s"
        return self.execute_query(query, (paper_id,), fetch_one=True, fetch_all=False)
    
    def get_by_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户试卷列表
        """
        query = "SELECT * FROM evaluation_papers WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        return self.execute_query(query, (user_id, limit), fetch_one=False, fetch_all=True) or []
    
    def update_question_count(self, paper_id: int, question_count: int) -> bool:
        """组卷完成后若实际题目数与抽题数不一致，同步 question_count。"""
        query = "UPDATE evaluation_papers SET question_count = %s WHERE id = %s"
        n = self.execute_update(query, (question_count, paper_id))
        return n > 0
    
    def delete(self, paper_id: int) -> bool:
        """
        删除试卷（evaluation_paper_items 等对 paper_id 的外键一般为 ON DELETE CASCADE）。
        用于组卷失败时回滚，避免卷表与题表长期不一致。
        """
        query = "DELETE FROM evaluation_papers WHERE id = %s"
        n = self.execute_update(query, (paper_id,))
        return n > 0
