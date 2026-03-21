"""
评测结果表CRUD操作
"""

from .base_crud import BaseCRUD
from typing import Optional, List, Dict, Any
from datetime import datetime


class EvaluationResultsCRUD(BaseCRUD):
    """评测结果表CRUD操作类"""
    
    def __init__(self):
        super().__init__("evaluation_results")
    
    def create(self, user_id: int, paper_id: int, score: float, correct_count: int,
               total_count: int, duration_seconds: int = None,
               assessed_level: str = None, submitted_at: datetime = None) -> Optional[int]:
        """
        创建评测结果
        """
        if submitted_at is None:
            submitted_at = datetime.now()
        self.log_operation("创建评测结果", user_id=user_id, paper_id=paper_id)
        query = """
        INSERT INTO evaluation_results (user_id, paper_id, score, correct_count, total_count,
            duration_seconds, assessed_level, submitted_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (
            user_id, paper_id, score, correct_count, total_count,
            duration_seconds, assessed_level, submitted_at
        ))
    
    def read(self, result_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取评测结果
        """
        query = "SELECT * FROM evaluation_results WHERE id = %s"
        return self.execute_query(query, (result_id,), fetch_one=True, fetch_all=False)
    
    def get_by_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户评测历史
        """
        query = """
        SELECT er.*, ep.paper_type, ep.question_count
        FROM evaluation_results er
        JOIN evaluation_papers ep ON er.paper_id = ep.id
        WHERE er.user_id = %s
        ORDER BY er.submitted_at DESC
        LIMIT %s
        """
        return self.execute_query(query, (user_id, limit), fetch_one=False, fetch_all=True) or []
