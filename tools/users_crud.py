"""
用户表CRUD操作
"""

from .base_crud import BaseCRUD
from typing import Optional, List, Dict, Any

class UsersCRUD(BaseCRUD):
    """用户表CRUD操作类"""
    
    def __init__(self):
        super().__init__("users")
    
    def create(self, username: str, password_hash: str, email: Optional[str] = None) -> Optional[int]:
        """
        创建新用户
        
        Args:
            username (str): 用户名
            password_hash (str): 密码哈希
            email (Optional[str]): 邮箱（可选）
            
        Returns:
            Optional[int]: 新创建的用户ID
        """
        self.log_operation("创建用户", username=username, email=email)
        
        # 验证必需字段
        if not self.validate_fields({"username": username, "password_hash": password_hash}, 
                                  ["username", "password_hash"]):
            return None
        
        query = """
        INSERT INTO users (username, email, password_hash)
        VALUES (%s, %s, %s)
        """
        params = (username, email, password_hash)
        
        user_id = self.execute_insert(query, params)
        if user_id:
            self.logger.info(f"成功创建用户，ID={user_id}")
        else:
            self.logger.error("创建用户失败")
        
        return user_id
    
    def read(self, user_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取用户信息
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            Optional[Dict[str, Any]]: 用户信息，如果不存在返回None
        """
        self.log_operation("读取用户", user_id=user_id)
        
        query = "SELECT * FROM users WHERE id = %s"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        
        if result:
            self.logger.info("找到用户")
        else:
            self.logger.info("用户不存在")
        
        return result
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取所有用户列表
        
        Args:
            limit (int): 限制返回记录数，默认100
            offset (int): 偏移量，默认0
            
        Returns:
            List[Dict[str, Any]]: 用户记录列表
        """
        self.log_operation("列出所有用户", limit=limit, offset=offset)
        
        query = "SELECT * FROM users LIMIT %s OFFSET %s"
        results = self.execute_query(query, (limit, offset), fetch_all=True)
        
        self.logger.info(f"返回{len(results)}个用户")
        return results or []
    
    def search(self, keyword: str, field: str = "username") -> List[Dict[str, Any]]:
        """
        搜索用户
        
        Args:
            keyword (str): 搜索关键词
            field (str): 搜索字段，默认为"username"，支持"id"和"username"
            
        Returns:
            List[Dict[str, Any]]: 匹配的用户记录列表
        """
        self.log_operation("搜索用户", keyword=keyword, field=field)
        
        if field == "id":
            query = "SELECT * FROM users WHERE id = %s"
            params = (keyword,)
        else:
            query = "SELECT * FROM users WHERE username LIKE %s"
            params = (f"%{keyword}%",)
        
        results = self.execute_query(query, params, fetch_all=True)
        self.logger.info(f"找到{len(results)}个匹配用户")
        return results or []
    
    def update(self, user_id: int, username: Optional[str] = None, 
               password_hash: Optional[str] = None, email: Optional[str] = None) -> int:
        """
        更新用户信息
        
        Args:
            user_id (int): 用户ID
            username (Optional[str]): 新用户名（可选）
            password_hash (Optional[str]): 新密码哈希（可选）
            email (Optional[str]): 新邮箱（可选）
            
        Returns:
            int: 受影响的行数
        """
        self.log_operation("更新用户", user_id=user_id, username=username, email=email)
        
        # 构建更新字段
        fields = {}
        if username is not None:
            fields['username'] = username
        if password_hash is not None:
            fields['password_hash'] = password_hash
        if email is not None:
            fields['email'] = email
        
        if not fields:
            self.logger.warning("没有要更新的字段")
            return 0
        
        query, params = self.build_update_query(fields, "id = %s")
        params = params + (user_id,)
        
        affected_rows = self.execute_update(query, params)
        self.logger.info(f"更新了{affected_rows}行")
        return affected_rows
    
    def delete(self, user_id: int) -> int:
        """
        删除用户
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            int: 受影响的行数
        """
        self.log_operation("删除用户", user_id=user_id)
        
        query = "DELETE FROM users WHERE id = %s"
        affected_rows = self.execute_update(query, (user_id,))
        
        self.logger.info(f"删除了{affected_rows}行")
        return affected_rows
    
    def update_model_filename(self, user_id: int, model_filename: str) -> int:
        """
        更新用户的模型文件名
        
        Args:
            user_id (int): 用户ID
            model_filename (str): 模型文件名
            
        Returns:
            int: 受影响的行数
        """
        self.log_operation("更新模型文件名", user_id=user_id, model_filename=model_filename)
        
        query = "UPDATE users SET model_filename = %s WHERE id = %s"
        affected_rows = self.execute_update(query, (model_filename, user_id))
        
        self.logger.info(f"更新了{affected_rows}行")
        return affected_rows
    
    def get_model_filename(self, user_id: int) -> Optional[str]:
        """
        获取用户的模型文件名
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            Optional[str]: 模型文件名，如果不存在返回None
        """
        self.log_operation("获取模型文件名", user_id=user_id)
        
        query = "SELECT model_filename FROM users WHERE id = %s"
        result = self.execute_query(query, (user_id,), fetch_one=True)
        
        return result['model_filename'] if result else None
    