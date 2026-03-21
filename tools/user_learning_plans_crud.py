"""
用户学习计划表CRUD操作
"""

from .base_crud import BaseCRUD
from typing import Optional, List, Dict, Any
from datetime import date, datetime


class UserLearningPlansCRUD(BaseCRUD):
    """用户学习计划表CRUD操作类"""
    
    def __init__(self):
        super().__init__("user_learning_plans")
    
    def create(self, user_id: int, dataset_type: str, daily_new_count: int = 20,
               daily_review_count: int = 20, plan_name: str = None,
               start_date: date = None, end_date: date = None,
               is_active: bool = True) -> Optional[int]:
        """
        创建学习计划
        """
        self.log_operation("创建学习计划", user_id=user_id, dataset_type=dataset_type)
        query = """
        INSERT INTO user_learning_plans (user_id, plan_name, dataset_type, daily_new_count,
            daily_review_count, start_date, end_date, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        return self.execute_insert(query, (
            user_id, plan_name, dataset_type, daily_new_count, daily_review_count,
            start_date, end_date, int(is_active)
        ))
    
    def read(self, plan_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取计划
        """
        query = "SELECT * FROM user_learning_plans WHERE id = %s"
        return self.execute_query(query, (plan_id,), fetch_one=True, fetch_all=False)
    
    def get_by_user(self, user_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """
        获取用户所有计划
        """
        query = "SELECT * FROM user_learning_plans WHERE user_id = %s ORDER BY created_at DESC LIMIT %s"
        return self.execute_query(query, (user_id, limit), fetch_one=False, fetch_all=True) or []
    
    def get_active_plan(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        获取用户当前生效的计划
        """
        query = "SELECT * FROM user_learning_plans WHERE user_id = %s AND is_active = 1 LIMIT 1"
        return self.execute_query(query, (user_id,), fetch_one=True, fetch_all=False)
    
    def update(self, plan_id: int, **kwargs) -> int:
        """
        更新计划
        """
        allowed = ['plan_name', 'dataset_type', 'daily_new_count', 'daily_review_count',
                   'start_date', 'end_date', 'is_active']
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return 0
        query, params = self.build_update_query(fields)
        return self.execute_update(query, params + (plan_id,))
    
    def deactivate(self, plan_id: int) -> int:
        """
        停用计划
        """
        return self.update(plan_id, is_active=False)
    
    def delete(self, plan_id: int) -> int:
        """
        删除计划
        """
        query = "DELETE FROM user_learning_plans WHERE id = %s"
        return self.execute_update(query, (plan_id,))
