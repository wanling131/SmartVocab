"""
数据库连接管理模块
简化版本，只保留必要的功能
"""

import logging
import mysql.connector
from mysql.connector import pooling
import threading
import os
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# 简化的数据库配置
DATABASE_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', '123456'),
    'database': os.getenv('DB_NAME', 'smartvocab'),
    'charset': 'utf8mb4',
    'autocommit': True,
    'pool_name': 'smart_vocab_pool',
    'pool_size': 10,
}

class DatabaseManager:
    """数据库管理器"""
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(DatabaseManager, cls).__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        
        self._pool = None
        self._initialized = True
        self._initialize_pool()
    
    def _initialize_pool(self):
        """初始化连接池"""
        try:
            self._pool = mysql.connector.pooling.MySQLConnectionPool(**DATABASE_CONFIG)
            logger.info("数据库连接池初始化成功，池大小: %s", DATABASE_CONFIG['pool_size'])
        except Exception as e:
            logger.error("数据库连接池初始化失败: %s", e)
            self._pool = None
    
    def get_connection(self) -> Optional[mysql.connector.connection.MySQLConnection]:
        """获取数据库连接"""
        if not self._pool:
            return None
        try:
            return self._pool.get_connection()
        except Exception as e:
            logger.warning("获取连接失败: %s", e)
            return None
    
    def return_connection(self, connection: mysql.connector.connection.MySQLConnection):
        """返回连接到连接池"""
        if connection:
            connection.close()
    
    def get_pool_status(self) -> Dict[str, Any]:
        """获取连接池状态"""
        if not self._pool:
            return {"status": "not_initialized"}
        
        return {
            "status": "active",
            "pool_name": DATABASE_CONFIG.get('pool_name', 'unknown'),
            "pool_size": DATABASE_CONFIG.get('pool_size', 0),
            "database": DATABASE_CONFIG.get('database', 'unknown'),
            "host": DATABASE_CONFIG.get('host', 'unknown')
        }

# 全局数据库管理器
_db_manager = DatabaseManager()

def get_database_context():
    """获取数据库连接上下文管理器"""
    return DatabaseConnection()

def get_pool_status() -> Dict[str, Any]:
    """获取连接池状态"""
    return _db_manager.get_pool_status()

def test_connection() -> bool:
    """测试数据库连接"""
    logger.info("=== 测试数据库连接 ===")
    
    pool_status = get_pool_status()
    logger.info("连接池状态: %s", pool_status)
    
    try:
        with get_database_context() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT VERSION()")
            version = cursor.fetchone()[0]
            logger.info("MySQL版本: %s", version)
            cursor.close()
            return True
    except Exception as e:
        logger.error("连接测试失败: %s", e)
        return False

class DatabaseConnection:
    """数据库连接上下文管理器"""
    
    def __init__(self):
        self.connection = None
    
    def __enter__(self) -> mysql.connector.connection.MySQLConnection:
        self.connection = _db_manager.get_connection()
        if not self.connection:
            raise Exception("无法获取数据库连接")
        return self.connection
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.connection:
            _db_manager.return_connection(self.connection)
            self.connection = None

if __name__ == "__main__":
    test_connection()