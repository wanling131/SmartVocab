"""
学习会话CRUD操作
提供学习会话的增删改查功能
"""

from tools.base_crud import BaseCRUD
from tools.database import get_database_context
from datetime import datetime
import json

class LearningSessionsCRUD(BaseCRUD):
    """学习会话CRUD操作类"""
    
    def __init__(self):
        super().__init__("learning_sessions")
    
    def create(self, user_id, session_data, session_type="learning"):
        """
        创建学习会话
        
        Args:
            user_id (int): 用户ID
            session_data (dict): 会话数据
            session_type (str): 会话类型 (learning/review/browse)
            
        Returns:
            int: 会话ID
        """
        print(f"DEBUG LearningSessionsCRUD.create: user_id={user_id}, session_type={session_type}")
        
        with get_database_context() as connection:
            cursor = connection.cursor()
            try:
                query = """
                INSERT INTO learning_sessions (user_id, session_type, session_data, 
                                             current_word_index, total_words, 
                                             created_at, updated_at, is_active)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                now = datetime.now()
                session_json = json.dumps(session_data, ensure_ascii=False, default=str)
                
                cursor.execute(query, (
                    user_id,
                    session_type,
                    session_json,
                    session_data.get('current_word_index', 0),
                    session_data.get('total_count', 0),
                    now,
                    now,
                    1  # is_active
                ))
                
                connection.commit()
                session_id = cursor.lastrowid
                print(f"DEBUG LearningSessionsCRUD.create: 成功创建会话，ID={session_id}")
                return session_id
                
            except Exception as e:
                print(f"DEBUG LearningSessionsCRUD.create: 创建会话失败: {e}")
                return None
            finally:
                cursor.close()
    
    def update(self, session_id, session_data=None, current_word_index=None, **kwargs):
        """
        更新学习会话
        
        Args:
            session_id (int): 会话ID
            session_data (dict): 更新的会话数据
            current_word_index (int): 当前单词索引
            **kwargs: 其他更新字段
            
        Returns:
            bool: 更新是否成功
        """
        print(f"DEBUG LearningSessionsCRUD.update: session_id={session_id}")
        
        update_fields = []
        params = []
        
        if session_data is not None:
            update_fields.append("session_data = %s")
            params.append(json.dumps(session_data, ensure_ascii=False, default=str))
        
        if current_word_index is not None:
            update_fields.append("current_word_index = %s")
            params.append(current_word_index)
        
        # 处理其他字段
        for key, value in kwargs.items():
            if key in ['total_words', 'is_active']:
                update_fields.append(f"{key} = %s")
                params.append(value)
        
        if not update_fields:
            return False
        
        update_fields.append("updated_at = %s")
        params.append(datetime.now())
        params.append(session_id)
        
        with get_database_context() as connection:
            cursor = connection.cursor()
            try:
                query = f"""
                UPDATE learning_sessions 
                SET {', '.join(update_fields)}
                WHERE id = %s
                """
                
                cursor.execute(query, params)
                connection.commit()
                affected_rows = cursor.rowcount
                
                print(f"DEBUG LearningSessionsCRUD.update: 更新了{affected_rows}行")
                return affected_rows > 0
                
            except Exception as e:
                print(f"DEBUG LearningSessionsCRUD.update: 更新失败: {e}")
                return False
            finally:
                cursor.close()
    
    def get_active_session(self, user_id, session_type="learning"):
        """
        获取用户的活跃会话
        
        Args:
            user_id (int): 用户ID
            session_type (str): 会话类型
            
        Returns:
            dict: 会话信息，包含session_data
        """
        print(f"DEBUG LearningSessionsCRUD.get_active_session: user_id={user_id}, session_type={session_type}")
        
        query = """
        SELECT * FROM learning_sessions 
        WHERE user_id = %s AND session_type = %s AND is_active = 1
        ORDER BY updated_at DESC
        LIMIT 1
        """
        
        result = self.execute_query(query, (user_id, session_type), fetch_one=True)
        
        if result:
            # 解析JSON数据
            try:
                result['session_data'] = json.loads(result['session_data'])
                print(f"DEBUG LearningSessionsCRUD.get_active_session: 找到活跃会话，ID={result['id']}")
            except json.JSONDecodeError as e:
                print(f"DEBUG LearningSessionsCRUD.get_active_session: JSON解析失败: {e}")
                result['session_data'] = {}
            
            return result
        
        print(f"DEBUG LearningSessionsCRUD.get_active_session: 未找到活跃会话")
        return None
    
    def deactivate_session(self, session_id):
        """
        停用会话
        
        Args:
            session_id (int): 会话ID
            
        Returns:
            bool: 操作是否成功
        """
        print(f"DEBUG LearningSessionsCRUD.deactivate_session: session_id={session_id}")
        
        return self.update(session_id, is_active=0)
    
    def get_by_user(self, user_id, limit=None, offset=0):
        """
        获取用户的所有会话
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量
            offset (int): 偏移量
            
        Returns:
            list: 会话列表
        """
        print(f"DEBUG LearningSessionsCRUD.get_by_user: user_id={user_id}, limit={limit}, offset={offset}")
        
        query = """
        SELECT * FROM learning_sessions 
        WHERE user_id = %s
        ORDER BY created_at DESC
        """
        params = [user_id]
        
        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)
        
        if offset > 0:
            query += " OFFSET %s"
            params.append(offset)
        
        results = self.execute_query(query, tuple(params), fetch_all=True)
        
        if results:
            # 解析每个会话的JSON数据
            for result in results:
                try:
                    result['session_data'] = json.loads(result['session_data'])
                except json.JSONDecodeError:
                    result['session_data'] = {}
            
            print(f"DEBUG LearningSessionsCRUD.get_by_user: 找到{len(results)}个会话")
        
        return results or []
