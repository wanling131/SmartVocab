import pandas as pd
import mysql.connector
import json
import os

# 数据库配置（从环境变量读取，fallback 用于本地开发）
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'database': os.getenv('DB_NAME', 'smartvocab'),
    'charset': 'utf8mb4'
}

def connect_to_mysql():
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            print("成功连接到MySQL数据库")
            return connection
    except Exception as e:
        print(f"连接MySQL失败: {e}")
        return None

def main():
    print("=== 将 dataset.csv 插入到MySQL数据库 ===")
    
    # 连接数据库
    connection = connect_to_mysql()
    if not connection:
        return
    
    cursor = connection.cursor()
    
    try:
        # 清空现有数据
        cursor.execute("DELETE FROM words")
        print("已清空words表")
        
        # 读取CSV文件
        df = pd.read_csv('data/dataset.csv')
        print(f"读取了 {len(df)} 条记录")
        
        inserted_count = 0
        
        for _, row in df.iterrows():
            try:
                # 处理领域分布
                spoken_ratio = float(row.get('spoken_ratio', 0)) if pd.notna(row.get('spoken_ratio')) else 0
                academic_ratio = float(row.get('academic_ratio', 0)) if pd.notna(row.get('academic_ratio')) else 0
                
                domain_list = []
                if spoken_ratio > 0.3:
                    domain_list.append('spoken')
                if academic_ratio > 0.3:
                    domain_list.append('academic')
                if not domain_list:
                    domain_list.append('general')
                
                # 插入数据
                insert_query = """
                INSERT INTO words (word, phonetic, translation, pos, tag, cefr_standard, 
                                 difficulty_level, frequency_rank, domain)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                
                cursor.execute(insert_query, (
                    str(row['word']).strip(),
                    str(row['phonetic']).strip(),
                    str(row['translation']).strip(),
                    str(row['pos']).strip(),
                    str(row['tag']).strip(),
                    str(row['cefr_standard']).strip(),
                    int(row['difficulty_level']),
                    int(row['total']),
                    json.dumps(domain_list, ensure_ascii=False)
                ))
                
                inserted_count += 1
                
                if inserted_count % 1000 == 0:
                    print(f"已插入 {inserted_count} 条记录")
                    
            except Exception as e:
                print(f"插入失败: {e}")
                continue
        
        connection.commit()
        print(f"成功插入 {inserted_count} 条记录")
        
        # 验证
        cursor.execute("SELECT COUNT(*) FROM words")
        total = cursor.fetchone()[0]
        print(f"数据库总记录数: {total}")
        
    except Exception as e:
        print(f"错误: {e}")
    finally:
        cursor.close()
        connection.close()

if __name__ == "__main__":
    main()
