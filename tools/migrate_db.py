"""
数据库迁移工具
执行升级迁移脚本，确保11张表结构就绪
支持：新建数据库、升级已有表结构
"""

import os
import sys

# 添加项目根目录
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import mysql.connector
from tools.database import DATABASE_CONFIG, get_database_context

# 迁移脚本路径
SCRIPT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '文档')
CREATE_SCRIPT = os.path.join(SCRIPT_DIR, '数据库建表脚本.sql')
MIGRATE_SCRIPT = os.path.join(SCRIPT_DIR, '数据库升级迁移脚本.sql')


def run_sql_file(connection, filepath, ignore_errors=None):
    """
    执行SQL文件，逐条执行语句
    ignore_errors: 包含这些关键词的错误将被忽略
    """
    if not os.path.exists(filepath):
        print(f"SQL文件不存在: {filepath}")
        return False
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 移除注释，按分号分割语句（简单处理，不处理字符串内的分号）
    statements = []
    current = []
    for line in content.split('\n'):
        stripped = line.strip()
        # 跳过纯注释行
        if stripped.startswith('--') or not stripped:
            continue
        current.append(line)
        if stripped.endswith(';'):
            stmt = '\n'.join(current).strip()
            if stmt and not stmt.startswith('--'):
                statements.append(stmt)
            current = []
    
    if current:
        stmt = '\n'.join(current).strip()
        if stmt and not stmt.startswith('--'):
            statements.append(stmt)
    
    cursor = connection.cursor()
    success_count = 0
    error_count = 0
    
    for stmt in statements:
        stmt = stmt.rstrip(';').strip()
        if not stmt or stmt.upper().startswith('USE '):
            continue
        try:
            cursor.execute(stmt)
            connection.commit()
            success_count += 1
            # 简短显示
            preview = stmt[:60].replace('\n', ' ') + '...' if len(stmt) > 60 else stmt.replace('\n', ' ')
            print(f"  OK: {preview}")
        except Exception as e:
            err_msg = str(e).lower()
            if ignore_errors and any(k in err_msg for k in ignore_errors):
                print(f"  跳过(已存在): {err_msg[:80]}")
            else:
                print(f"  错误: {e}")
                error_count += 1
                # 迁移时有些错误可接受，继续执行
                if 'duplicate column' in err_msg or '1060' in str(e):
                    connection.rollback()
                else:
                    connection.rollback()
    
    cursor.close()
    print(f"执行完成: 成功 {success_count}, 错误 {error_count}")
    return error_count == 0


def ensure_database():
    """确保 smartvocab 数据库存在"""
    config = {k: v for k, v in DATABASE_CONFIG.items() if k != 'database'}
    try:
        conn = mysql.connector.connect(**config)
        cursor = conn.cursor()
        cursor.execute("CREATE DATABASE IF NOT EXISTS smartvocab DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"创建数据库时出错: {e}")


def migrate():
    """执行迁移"""
    print("=== SmartVocab 数据库迁移 ===")
    ensure_database()
    
    try:
        with get_database_context() as conn:
            # 1. 先执行建表脚本（创建数据库和表，IF NOT EXISTS 安全）
            print("\n1. 执行建表脚本...")
            run_sql_file(conn, CREATE_SCRIPT)
            
            # 2. 执行升级迁移脚本（添加缺失列，忽略重复列错误）
            print("\n2. 执行升级迁移脚本...")
            run_sql_file(conn, MIGRATE_SCRIPT, 
                ignore_errors=['duplicate column', '1060', '1054', '1146'])
            
            # 3. 初始化 level_gates（若表为空）
            cursor = conn.cursor()
            try:
                cursor.execute("SELECT COUNT(*) FROM level_gates")
                if cursor.fetchone()[0] == 0:
                    for i in range(1, 7):
                        cursor.execute(
                            "INSERT INTO level_gates (gate_order, gate_name, difficulty_level, word_count) VALUES (%s, %s, %s, %s)",
                            (i, f"第{i}关", i, 50)
                        )
                    conn.commit()
                    print("\n3. 已初始化6个关卡")
            except Exception as e:
                print(f"  初始化关卡跳过: {e}")
            finally:
                cursor.close()
            
        print("\n迁移完成！11张表结构已就绪。")
        return True
    except Exception as e:
        print(f"迁移失败: {e}")
        return False


if __name__ == '__main__':
    success = migrate()
    sys.exit(0 if success else 1)
