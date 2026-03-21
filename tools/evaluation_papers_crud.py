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
