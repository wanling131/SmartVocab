"""
学习记录表CRUD操作
"""

import logging
import mysql.connector
from .database import get_database_context

logger = logging.getLogger(__name__)


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
        logger.debug("LearningRecordsCRUD.list_all: limit=%s, offset=%s", limit, offset)
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM user_learning_records LIMIT %s OFFSET %s"
                cursor.execute(query, (limit, offset))
                results = cursor.fetchall()
                logger.debug("LearningRecordsCRUD.list_all: 返回%s条记录", len(results))
                return results
            except Exception as e:
                logger.warning("LearningRecordsCRUD.list_all: 查询失败: %s", e)
                return []
            finally:
                cursor.close()
    
    def create(self, user_id, word_id, mastery_level=0.0, last_reviewed_at=None, 
               review_count=0, is_mastered=False, first_learned_at=None, 
               next_review_at=None, level_gate_id=None):
        """
        创建学习记录
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            mastery_level (float): 掌握程度
            last_reviewed_at (datetime): 最后复习时间
            review_count (int): 复习次数
            is_mastered (bool): 是否已掌握
            first_learned_at (datetime): 首次学习时间（默认等于 last_reviewed_at）
            next_review_at (datetime): 下次复习时间（由遗忘曲线计算）
            level_gate_id (int): 关卡ID（闯关模式）
            
        Returns:
            int: 新创建的记录ID
        """
        from datetime import datetime
        if last_reviewed_at is None:
            last_reviewed_at = datetime.now()
        if first_learned_at is None:
            first_learned_at = last_reviewed_at
            
        with get_database_context() as connection:
            cursor = connection.cursor()
            try:
                query = """
                INSERT INTO user_learning_records (user_id, word_id, level_gate_id,
                    first_learned_at, last_reviewed_at, next_review_at,
                    mastery_level, review_count, is_mastered)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(query, (user_id, word_id, level_gate_id,
                    first_learned_at, last_reviewed_at, next_review_at,
                    mastery_level, review_count, is_mastered))
                connection.commit()
                record_id = cursor.lastrowid
                return record_id
            except Exception as e:
                # 兼容未迁移 DB：若列不存在则使用旧版 INSERT
                if 'Unknown column' in str(e) or 'first_learned_at' in str(e) or 'next_review_at' in str(e):
                    try:
                        query = """
                        INSERT INTO user_learning_records (user_id, word_id, last_reviewed_at,
                            mastery_level, review_count, is_mastered)
                        VALUES (%s, %s, %s, %s, %s, %s)
                        """
                        cursor.execute(query, (user_id, word_id, last_reviewed_at,
                            mastery_level, review_count, is_mastered))
                        connection.commit()
                        return cursor.lastrowid
                    except Exception as e2:
                        logger.warning("LearningRecordsCRUD.create: 创建记录失败: %s", e2)
                        return None
                else:
                    logger.warning("LearningRecordsCRUD.create: 创建记录失败: %s", e)
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
        logger.debug("LearningRecordsCRUD.read: record_id=%s", record_id)
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM user_learning_records WHERE id = %s"
                cursor.execute(query, (record_id,))
                result = cursor.fetchone()
                logger.debug("LearningRecordsCRUD.read: 查询结果=%s", '找到记录' if result else '记录不存在')
                return result
            except Exception as e:
                logger.warning("LearningRecordsCRUD.read: 查询记录失败: %s", e)
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
        logger.debug("LearningRecordsCRUD.update: record_id=%s, kwargs=%s", record_id, kwargs)
        if not kwargs:
            logger.debug("LearningRecordsCRUD.update: 没有要更新的字段")
            return 0
        
        set_clauses = []
        values = []
        
        # 允许更新的字段（含记忆曲线相关）
        allowed_map = {
            'is_learned': 'is_mastered', 'last_reviewed': 'last_reviewed_at',
            'mastery_level': 'mastery_level', 'review_count': 'review_count',
            'is_mastered': 'is_mastered', 'last_reviewed_at': 'last_reviewed_at',
            'first_learned_at': 'first_learned_at', 'next_review_at': 'next_review_at',
            'level_gate_id': 'level_gate_id',
        }
        for field, value in kwargs.items():
            if field in allowed_map:
                db_field = allowed_map[field]
                set_clauses.append(f"{db_field} = %s")
                values.append(value)
        
        if not set_clauses:
            logger.debug("LearningRecordsCRUD.update: 没有有效的更新字段")
            return 0
        
        values.append(record_id)
        
        with get_database_context() as connection:
            cursor = connection.cursor()
            query = f"UPDATE user_learning_records SET {', '.join(set_clauses)} WHERE id = %s"
            cursor.execute(query, values)
            connection.commit()
            affected_rows = cursor.rowcount
            logger.debug("LearningRecordsCRUD.update: 更新了%s行", affected_rows)
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
        logger.debug("LearningRecordsCRUD.delete: record_id=%s", record_id)
        with get_database_context() as connection:
            cursor = connection.cursor()
            try:
                query = "DELETE FROM user_learning_records WHERE id = %s"
                cursor.execute(query, (record_id,))
                connection.commit()
                affected_rows = cursor.rowcount
                logger.debug("LearningRecordsCRUD.delete: 删除了%s行", affected_rows)
                return affected_rows
            except Exception as e:
                logger.warning("LearningRecordsCRUD.delete: 删除记录失败: %s", e)
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
        logger.debug("LearningRecordsCRUD.get_by_user: user_id=%s, limit=%s, offset=%s", user_id, limit, offset)
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
                logger.debug("LearningRecordsCRUD.get_by_user: 找到%s条记录", len(results))
                return results
            except Exception as e:
                logger.warning("LearningRecordsCRUD.get_by_user: 查询失败: %s", e)
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
        logger.debug("LearningRecordsCRUD.search_by_user_word: user_id=%s, word_id=%s", user_id, word_id)
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = "SELECT * FROM user_learning_records WHERE user_id = %s AND word_id = %s"
                cursor.execute(query, (user_id, word_id))
                results = cursor.fetchall()
                logger.debug("LearningRecordsCRUD.search_by_user_word: 找到%s条记录", len(results))
                return results
            except Exception as e:
                logger.warning("LearningRecordsCRUD.search_by_user_word: 查询失败: %s", e)
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
    
    def get_review_due(self, user_id, limit=20, offset=0):
        """
        获取到期需复习的记录（next_review_at <= now）
        若表无 next_review_at 列则回退到 get_by_user
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量
            offset (int): 偏移量
            
        Returns:
            list: 到期复习记录列表
        """
        with get_database_context() as connection:
            cursor = connection.cursor(dictionary=True)
            try:
                query = """
                SELECT * FROM user_learning_records 
                WHERE user_id = %s AND (next_review_at IS NULL OR next_review_at <= NOW())
                ORDER BY COALESCE(next_review_at, '1970-01-01') ASC, last_reviewed_at ASC
                LIMIT %s OFFSET %s
                """
                cursor.execute(query, (user_id, limit, offset))
                return cursor.fetchall()
            except Exception as e:
                # 若 next_review_at 列不存在，回退到按 last_reviewed 获取
                if 'next_review_at' in str(e) or 'Unknown column' in str(e):
                    return self.get_by_user(user_id, limit, offset)
                raise
            finally:
                cursor.close()
    
    def close(self):
        """兼容性方法：使用连接池时无需手动关闭"""
        pass
    
def main():
    """
    测试函数
    演示学习记录表CRUD工具的基本用法
    """
    crud = LearningRecordsCRUD()
    
    from config import configure_logging
    configure_logging()
    logger.info("=== 学习记录CRUD工具 ===")
    
    # 列出所有学习记录
    records = crud.list_all(limit=5)
    logger.info("学习记录数量: %s", len(records))
    
    crud.close()

if __name__ == "__main__":
    main()
