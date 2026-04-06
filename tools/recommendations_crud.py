"""
推荐记录表CRUD操作
"""

import logging
import mysql.connector
from .database import get_database_context

logger = logging.getLogger(__name__)

class RecommendationsCRUD:
    """推荐记录表CRUD操作类"""
    
    def __init__(self):
        pass
    
    def list_all(self, limit=100, offset=0):
        """
        获取所有推荐记录列表
        
        Args:
            limit (int): 限制返回记录数，默认100
            offset (int): 偏移量，默认0
            
        Returns:
            list: 推荐记录列表，每个记录包含所有字段信息
        """
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM recommendations LIMIT %s OFFSET %s"
                cursor.execute(query, (limit, offset))
                return cursor.fetchall()
            except Exception as e:
                logger.error(f"查询失败: {e}")
                return []
            finally:
                cursor.close()
    
    def create(self, user_id, word_id, recommendation_score=0.5, 
               recommendation_type="mixed", reason=None, created_at=None):
        """
        创建推荐记录
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            recommendation_score (float): 推荐分数
            recommendation_type (str): 推荐算法类型
            reason (str): 推荐理由
            created_at (datetime): 创建时间
            
        Returns:
            int: 新创建的记录ID
        """
        if created_at is None:
            from datetime import datetime
            created_at = datetime.now()
            
        with get_database_context() as connection:
            cursor = connection.cursor()
            query = """
            INSERT INTO recommendations (user_id, word_id, recommendation_score, 
                                       recommendation_type, reason, created_at)
            VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(query, (user_id, word_id, recommendation_score, 
                                  recommendation_type, reason, created_at))
            connection.commit()
            record_id = cursor.lastrowid
            cursor.close()
            return record_id
    
    def read(self, record_id):
        """
        根据ID读取推荐记录
        
        Args:
            record_id (int): 记录ID
            
        Returns:
            dict: 推荐记录信息，如果不存在返回None
        """
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            query = "SELECT * FROM recommendations WHERE id = %s"
            cursor.execute(query, (record_id,))
            result = cursor.fetchone()
            cursor.close()
            return result
    
    def update(self, record_id, **kwargs):
        """
        更新推荐记录
        
        Args:
            record_id (int): 记录ID
            **kwargs: 要更新的字段和值
            
        Returns:
            int: 受影响的行数
        """
        if not kwargs:
            return 0
        
        set_clauses = []
        values = []
        
        for field, value in kwargs.items():
            if field in ['recommendation_score', 'recommendation_type', 'reason']:
                set_clauses.append(f"{field} = %s")
                values.append(value)
        
        if not set_clauses:
            return 0
        
        values.append(record_id)
        
        with get_database_context() as connection:
            cursor = connection.cursor()
            query = f"UPDATE recommendations SET {', '.join(set_clauses)} WHERE id = %s"
            cursor.execute(query, values)
            connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
    
    def delete(self, record_id):
        """
        删除推荐记录
        
        Args:
            record_id (int): 记录ID
            
        Returns:
            int: 受影响的行数
        """
        with get_database_context() as connection:
            cursor = connection.cursor()
            query = "DELETE FROM recommendations WHERE id = %s"
            cursor.execute(query, (record_id,))
            connection.commit()
            affected_rows = cursor.rowcount
            cursor.close()
            return affected_rows
    
    def get_by_user(self, user_id, limit=None, offset=0):
        """
        获取指定用户的推荐记录
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量
            offset (int): 偏移量
            
        Returns:
            list: 该用户的推荐记录列表
        """
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                if limit:
                    query = "SELECT * FROM recommendations WHERE user_id = %s LIMIT %s OFFSET %s"
                    cursor.execute(query, (user_id, limit, offset))
                else:
                    query = "SELECT * FROM recommendations WHERE user_id = %s"
                    cursor.execute(query, (user_id,))
                return cursor.fetchall()
            except Exception as e:
                logger.error(f"查询失败: {e}")
                return []
            finally:
                cursor.close()
    
    def get_user_recommendations(self, user_id):
        """
        获取指定用户的推荐记录（兼容性方法）
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            list: 该用户的推荐记录列表
        """
        return self.get_by_user(user_id)
    
    
def main():
    """
    测试函数
    演示推荐记录表CRUD工具的基本用法
    """
    crud = RecommendationsCRUD()
    
    print("=== 推荐记录CRUD工具 ===")
    
    # 列出所有推荐记录
    recommendations = crud.list_all(limit=5)
    print(f"推荐记录数量: {len(recommendations)}")
    
    crud.close()

if __name__ == "__main__":
    main()
