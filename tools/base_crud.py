"""
CRUD基础类 - 提供统一的数据库操作接口
"""

import logging
from typing import Optional, List, Dict, Any, Union
from contextlib import contextmanager
from .database import get_database_context

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BaseCRUD:
    """CRUD基础类，提供统一的数据库操作接口"""
    
    def __init__(self, table_name: str):
        """
        初始化CRUD基础类
        
        Args:
            table_name (str): 数据库表名
        """
        self.table_name = table_name
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
    
    @contextmanager
    def get_cursor(self, connection=None, dictionary=True):
        """
        获取数据库游标的上下文管理器
        
        Args:
            connection: 数据库连接，如果为None则使用连接池
            dictionary: 是否返回字典格式结果
            
        Yields:
            cursor: 数据库游标
        """
        if connection:
            # 使用提供的连接
            cursor = connection.cursor(dictionary=dictionary)
            try:
                yield cursor
            finally:
                cursor.close()
        else:
            # 使用连接池
            with get_database_context() as conn:
                cursor = conn.cursor(dictionary=dictionary)
                try:
                    yield cursor
                finally:
                    cursor.close()
    
    def execute_query(self, query: str, params: tuple = None, 
                     fetch_one: bool = False, fetch_all: bool = True) -> Union[Dict, List, None]:
        """
        执行查询语句
        
        Args:
            query (str): SQL查询语句
            params (tuple): 查询参数
            fetch_one (bool): 是否只获取一条记录
            fetch_all (bool): 是否获取所有记录
            
        Returns:
            Union[Dict, List, None]: 查询结果
        """
        try:
            with self.get_cursor() as cursor:
                cursor.execute(query, params or ())
                
                if fetch_one:
                    return cursor.fetchone()
                elif fetch_all:
                    return cursor.fetchall()
                else:
                    return cursor.rowcount
        except Exception as e:
            self.logger.error(f"查询执行失败: {e}, SQL: {query}, 参数: {params}")
            return None if fetch_one or fetch_all else 0
    
    def execute_update(self, query: str, params: tuple = None) -> int:
        """
        执行更新语句（INSERT, UPDATE, DELETE）
        
        Args:
            query (str): SQL语句
            params (tuple): 参数
            
        Returns:
            int: 受影响的行数
        """
        try:
            with get_database_context() as connection:
                with self.get_cursor(connection, dictionary=False) as cursor:
                    cursor.execute(query, params or ())
                    connection.commit()
                    return cursor.rowcount
        except Exception as e:
            self.logger.error(f"更新执行失败: {e}, SQL: {query}, 参数: {params}")
            return 0
    
    def execute_insert(self, query: str, params: tuple = None) -> Optional[int]:
        """
        执行插入语句
        
        Args:
            query (str): SQL语句
            params (tuple): 参数
            
        Returns:
            Optional[int]: 新插入记录的ID
        """
        try:
            with get_database_context() as connection:
                with self.get_cursor(connection, dictionary=False) as cursor:
                    cursor.execute(query, params or ())
                    connection.commit()
                    return cursor.lastrowid
        except Exception as e:
            self.logger.error(f"插入执行失败: {e}, SQL: {query}, 参数: {params}")
            return None
    
    def build_update_query(self, fields: Dict[str, Any], where_clause: str = "id = %s",
                          allowed_fields: List[str] = None) -> tuple:
        """
        构建更新查询语句

        Args:
            fields (Dict[str, Any]): 要更新的字段和值
            where_clause (str): WHERE子句
            allowed_fields (List[str]): 允许更新的字段白名单，None表示不限制

        Returns:
            tuple: (query, params)
        """
        if not fields:
            return "", ()

        set_clauses = []
        values = []

        for field, value in fields.items():
            # 白名单过滤：只允许合法列名
            if allowed_fields and field not in allowed_fields:
                continue
            set_clauses.append(f"{field} = %s")
            values.append(value)

        if not set_clauses:
            return "", ()

        query = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {where_clause}"
        return query, tuple(values)
    
    def validate_fields(self, data: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        验证必需字段
        
        Args:
            data (Dict[str, Any]): 数据字典
            required_fields (List[str]): 必需字段列表
            
        Returns:
            bool: 验证是否通过
        """
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            self.logger.warning(f"缺少必需字段: {missing_fields}")
            return False
        return True
    
    def log_operation(self, operation: str, **kwargs):
        """
        记录操作日志
        
        Args:
            operation (str): 操作名称
            **kwargs: 操作参数
        """
        self.logger.info(f"{operation}: {kwargs}")
    
    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        pass
