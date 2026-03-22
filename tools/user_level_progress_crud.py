"""
用户关卡进度表CRUD操作
"""

from .base_crud import BaseCRUD
from typing import Optional, List, Dict, Any


class UserLevelProgressCRUD(BaseCRUD):
    """用户关卡进度表CRUD操作类"""
    
    def __init__(self):
        super().__init__("user_level_progress")
    
    def create(self, user_id: int, level_gate_id: int, mastered_count: int = 0,
               is_unlocked: bool = False, is_completed: bool = False,
               completed_at=None) -> Optional[int]:
        """
        创建用户关卡进度
        """
        self.log_operation("创建关卡进度", user_id=user_id, level_gate_id=level_gate_id)
        query = """
        INSERT INTO user_level_progress (user_id, level_gate_id, mastered_count, 
            is_unlocked, is_completed, completed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (
            user_id, level_gate_id, mastered_count, 
            int(is_unlocked), int(is_completed), completed_at
        ))
    
    def read(self, progress_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取进度
        """
        query = "SELECT * FROM user_level_progress WHERE id = %s"
        return self.execute_query(query, (progress_id,), fetch_one=True, fetch_all=False)
    
    def get_by_user(self, user_id: int) -> List[Dict[str, Any]]:
        """
        获取用户所有关卡进度
        """
        query = """
        SELECT ulp.*, lg.gate_order, lg.gate_name, lg.difficulty_level, lg.word_count
        FROM user_level_progress ulp
        JOIN level_gates lg ON ulp.level_gate_id = lg.id
        WHERE ulp.user_id = %s
        ORDER BY lg.gate_order ASC
        """
        return self.execute_query(query, (user_id,), fetch_one=False, fetch_all=True) or []
    
    def get_by_user_gate(self, user_id: int, level_gate_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户指定关卡的进度
        """
        query = "SELECT * FROM user_level_progress WHERE user_id = %s AND level_gate_id = %s"
        return self.execute_query(query, (user_id, level_gate_id), fetch_one=True, fetch_all=False)
    
    def update_progress(self, progress_id: int, mastered_count: int = None,
                        is_unlocked: bool = None, is_completed: bool = None,
                        completed_at=None) -> int:
        """
        更新进度
        """
        fields = {}
        if mastered_count is not None:
            fields['mastered_count'] = mastered_count
        if is_unlocked is not None:
            fields['is_unlocked'] = int(is_unlocked)
        if is_completed is not None:
            fields['is_completed'] = int(is_completed)
        if completed_at is not None:
            fields['completed_at'] = completed_at
        if not fields:
            return 0
        query, params = self.build_update_query(fields)
        return self.execute_update(query, params + (progress_id,))
    
    def unlock_gate(self, user_id: int, level_gate_id: int) -> bool:
        """
        解锁关卡（设置 is_unlocked=1）
        """
        progress = self.get_by_user_gate(user_id, level_gate_id)
        if progress:
            return self.update_progress(progress['id'], is_unlocked=True) > 0
        # 若不存在则创建并解锁
        pid = self.create(user_id, level_gate_id, is_unlocked=True)
        return pid is not None
    
    def ensure_progress_exists(self, user_id: int, level_gate_id: int) -> Optional[Dict[str, Any]]:
        """
        确保用户有关卡进度记录，若无则创建
        """
        progress = self.get_by_user_gate(user_id, level_gate_id)
        if progress:
            return progress
        pid = self.create(user_id, level_gate_id, mastered_count=0,
                          is_unlocked=False, is_completed=False)
        return self.read(pid) if pid else None

    def update_progress_by_user_gate(self, user_id: int, level_gate_id: int,
                                      mastered_count: int = None,
                                      is_completed: bool = None) -> bool:
        """
        通过 user_id 和 level_gate_id 更新进度
        """
        progress = self.get_by_user_gate(user_id, level_gate_id)
        if not progress:
            return False

        fields = {}
        if mastered_count is not None:
            fields['mastered_count'] = mastered_count
        if is_completed is not None:
            fields['is_completed'] = int(is_completed)
            if is_completed:
                from datetime import datetime
                fields['completed_at'] = datetime.now()

        if not fields:
            return True

        query, params = self.build_update_query(fields)
        result = self.execute_update(query, params + (progress['id'],))
        return result > 0
