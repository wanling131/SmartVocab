"""
学习记录表CRUD操作
"""

import mysql.connector
from .database import get_database_context

class LearningRecordsCRUD:
    """学习记录表CRUD操作类"""
    
    def __init__(self):
        pass
    
    def list_all(self, limit=100, offset=0):
        """
        获取所有学习记录列表
        
        Args:
            limit (int): 限制返回记录数，默认100
            offset (int): 偏移量，默认0
            
        Returns:
            list: 学习记录列表，每个记录包含所有字段信息
        """
        print(f"DEBUG LearningRecordsCRUD.list_all: limit={limit}, offset={offset}")
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM user_learning_records LIMIT %s OFFSET %s"
                cursor.execute(query, (limit, offset))
                results = cursor.fetchall()
                print(f"DEBUG LearningRecordsCRUD.list_all: 返回{len(results)}条记录")
                return results
            except Exception as e:
                print(f"DEBUG LearningRecordsCRUD.list_all: 查询失败: {e}")
                return []
            finally:
                cursor.close()
    
    def create(self, user_id, word_id, mastery_level=0.0, last_reviewed_at=None, 
               review_count=0, is_mastered=False):
        """
        创建学习记录
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            mastery_level (float): 掌握程度
            last_reviewed_at (datetime): 最后复习时间
            review_count (int): 复习次数
            is_mastered (bool): 是否已掌握
            
        Returns:
            int: 新创建的记录ID
        """
        print(f"DEBUG LearningRecordsCRUD.create: user_id={user_id}, word_id={word_id}, mastery_level={mastery_level}, is_mastered={is_mastered}")
        
        # 如果没有提供最后复习时间，使用当前时间
        if last_reviewed_at is None:
            from datetime import datetime
            last_reviewed_at = datetime.now()
            
        with get_database_context() as connection:
            cursor = connection.cursor()
            try:
                query = """
                INSERT INTO user_learning_records (user_id, word_id, last_reviewed_at, 
                                                 mastery_level, review_count, is_mastered)
                VALUES (%s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (user_id, word_id, last_reviewed_at, 
                                      mastery_level, review_count, is_mastered))
                connection.commit()
                record_id = cursor.lastrowid
                print(f"DEBUG LearningRecordsCRUD.create: 成功创建记录，ID={record_id}")
                return record_id
            except Exception as e:
                print(f"DEBUG LearningRecordsCRUD.create: 创建记录失败: {e}")
                return None
            finally:
                cursor.close()
    
    def read(self, record_id):
        """
        根据ID读取学习记录
        
        Args:
            record_id (int): 记录ID
            
        Returns:
            dict: 学习记录信息，如果不存在返回None
        """
        print(f"DEBUG LearningRecordsCRUD.read: record_id={record_id}")
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM user_learning_records WHERE id = %s"
                cursor.execute(query, (record_id,))
                result = cursor.fetchone()
                print(f"DEBUG LearningRecordsCRUD.read: 查询结果={'找到记录' if result else '记录不存在'}")
                return result
            except Exception as e:
                print(f"DEBUG LearningRecordsCRUD.read: 查询记录失败: {e}")
                return None
            finally:
                cursor.close()
    
    def update(self, record_id, **kwargs):
        """
        更新学习记录
        
        Args:
            record_id (int): 记录ID
            **kwargs: 要更新的字段和值
            
        Returns:
            int: 受影响的行数
        """
        print(f"DEBUG LearningRecordsCRUD.update: record_id={record_id}, kwargs={kwargs}")
        if not kwargs:
            print("DEBUG LearningRecordsCRUD.update: 没有要更新的字段")
            return 0
        
        set_clauses = []
        values = []
        
        for field, value in kwargs.items():
            if field in ['mastery_level', 'review_count', 'is_learned', 'last_reviewed']:
                # 映射字段名称
                if field == 'is_learned':
                    field = 'is_mastered'
                elif field == 'last_reviewed':
                    field = 'last_reviewed_at'
                set_clauses.append(f"{field} = %s")
                values.append(value)
        
        if not set_clauses:
            print("DEBUG LearningRecordsCRUD.update: 没有有效的更新字段")
            return 0
        
        values.append(record_id)
        
        with get_database_context() as connection:
            cursor = connection.cursor()
            query = f"UPDATE user_learning_records SET {', '.join(set_clauses)} WHERE id = %s"
            cursor.execute(query, values)
            connection.commit()
            affected_rows = cursor.rowcount
            print(f"DEBUG LearningRecordsCRUD.update: 更新了{affected_rows}行")
            cursor.close()
            return affected_rows
    
    def delete(self, record_id):
        """
        删除学习记录
        
        Args:
            record_id (int): 记录ID
            
        Returns:
            int: 受影响的行数
        """
        print(f"DEBUG LearningRecordsCRUD.delete: record_id={record_id}")
        with get_database_context() as connection:
            cursor = connection.cursor()
            try:
                query = "DELETE FROM user_learning_records WHERE id = %s"
                cursor.execute(query, (record_id,))
                connection.commit()
                affected_rows = cursor.rowcount
                print(f"DEBUG LearningRecordsCRUD.delete: 删除了{affected_rows}行")
                return affected_rows
            except Exception as e:
                print(f"DEBUG LearningRecordsCRUD.delete: 删除记录失败: {e}")
                return 0
            finally:
                cursor.close()
    
    def get_by_user(self, user_id, limit=None, offset=0):
        """
        获取指定用户的学习记录
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量
            offset (int): 偏移量
            
        Returns:
            list: 该用户的学习记录列表
        """
        print(f"DEBUG LearningRecordsCRUD.get_by_user: user_id={user_id}, limit={limit}, offset={offset}")
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                if limit:
                    query = "SELECT * FROM user_learning_records WHERE user_id = %s ORDER BY last_reviewed_at DESC LIMIT %s OFFSET %s"
                    cursor.execute(query, (user_id, limit, offset))
                else:
                    query = "SELECT * FROM user_learning_records WHERE user_id = %s ORDER BY last_reviewed_at DESC"
                    cursor.execute(query, (user_id,))
                results = cursor.fetchall()
                print(f"DEBUG LearningRecordsCRUD.get_by_user: 找到{len(results)}条记录")
                return results
            except Exception as e:
                print(f"DEBUG LearningRecordsCRUD.get_by_user: 查询失败: {e}")
                return []
            finally:
                cursor.close()
    
    def search_by_user_word(self, user_id, word_id):
        """
        根据用户ID和单词ID搜索学习记录
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            
        Returns:
            list: 匹配的学习记录列表
        """
        print(f"DEBUG LearningRecordsCRUD.search_by_user_word: user_id={user_id}, word_id={word_id}")
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM user_learning_records WHERE user_id = %s AND word_id = %s"
                cursor.execute(query, (user_id, word_id))
                results = cursor.fetchall()
                print(f"DEBUG LearningRecordsCRUD.search_by_user_word: 找到{len(results)}条记录")
                return results
            except Exception as e:
                print(f"DEBUG LearningRecordsCRUD.search_by_user_word: 查询失败: {e}")
                return []
            finally:
                cursor.close()
    
    def get_user_records(self, user_id):
        """
        获取指定用户的学习记录（兼容性方法）
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            list: 该用户的学习记录列表
        """
        return self.get_by_user(user_id)
    
    
def main():
    """
    测试函数
    演示学习记录表CRUD工具的基本用法
    """
    crud = LearningRecordsCRUD()
    
    print("=== 学习记录CRUD工具 ===")
    
    # 列出所有学习记录
    records = crud.list_all(limit=5)
    print(f"学习记录数量: {len(records)}")
    
    crud.close()

if __name__ == "__main__":
    main()
