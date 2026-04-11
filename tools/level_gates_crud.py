"""
闯关关卡表CRUD操作
"""

from typing import Any, Dict, List, Optional

from .base_crud import BaseCRUD


class LevelGatesCRUD(BaseCRUD):
    """闯关关卡表CRUD操作类"""

    def __init__(self):
        super().__init__("level_gates")

    def create(
        self, gate_order: int, gate_name: str, difficulty_level: int, word_count: int
    ) -> Optional[int]:
        """
        创建关卡

        Args:
            gate_order (int): 关卡序号
            gate_name (str): 关卡名称
            difficulty_level (int): 难度等级 1-6
            word_count (int): 词汇数量

        Returns:
            Optional[int]: 新创建的关卡ID
        """
        self.log_operation("创建关卡", gate_order=gate_order, gate_name=gate_name)
        query = """
        INSERT INTO level_gates (gate_order, gate_name, difficulty_level, word_count)
        VALUES (%s, %s, %s, %s)
        """
        return self.execute_insert(query, (gate_order, gate_name, difficulty_level, word_count))

    def read(self, gate_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取关卡
        """
        query = "SELECT * FROM level_gates WHERE id = %s"
        return self.execute_query(query, (gate_id,), fetch_one=True, fetch_all=False)

    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取所有关卡列表（按 gate_order 排序）
        """
        query = "SELECT * FROM level_gates ORDER BY gate_order ASC LIMIT %s OFFSET %s"
        return self.execute_query(query, (limit, offset), fetch_one=False, fetch_all=True) or []

    def get_by_difficulty(self, difficulty_level: int) -> List[Dict[str, Any]]:
        """
        按难度等级获取关卡
        """
        query = "SELECT * FROM level_gates WHERE difficulty_level = %s ORDER BY gate_order ASC"
        return self.execute_query(query, (difficulty_level,), fetch_one=False, fetch_all=True) or []

    def update(self, gate_id: int, **kwargs) -> int:
        """
        更新关卡
        """
        allowed = ["gate_order", "gate_name", "difficulty_level", "word_count"]
        fields = {k: v for k, v in kwargs.items() if k in allowed}
        if not fields:
            return 0
        query, params = self.build_update_query(fields)
        if not query:
            return 0
        params = params + (gate_id,)
        return self.execute_update(query, params)

    def delete(self, gate_id: int) -> int:
        """
        删除关卡
        """
        query = "DELETE FROM level_gates WHERE id = %s"
        return self.execute_update(query, (gate_id,))
