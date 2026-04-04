"""
词汇表CRUD操作（带缓存优化）
"""

import json
import logging
from .base_crud import BaseCRUD
from typing import Optional, List, Dict, Any
from .memory_cache import (
    word_cache, word_list_cache,
    make_word_key, make_word_list_key, invalidate_word_cache
)

logger = logging.getLogger(__name__)


class WordsCRUD(BaseCRUD):
    """词汇表CRUD操作类（带缓存优化）"""

    def __init__(self):
        super().__init__("words")
    
    def _parse_domain_field(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        解析domain字段的JSON数据
        
        Args:
            results (List[Dict[str, Any]]): 查询结果列表
            
        Returns:
            List[Dict[str, Any]]: 解析后的结果列表
        """
        for result in results:
            if result.get("domain"):
                try:
                    result["domain"] = json.loads(result["domain"])
                except json.JSONDecodeError:
                    self.logger.warning(f"无法解析domain字段: {result.get('domain')}")
                    result["domain"] = {}
        return results
    
    def list_all(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        获取所有单词列表
        
        Args:
            limit (int): 限制返回记录数，默认100
            offset (int): 偏移量，默认0
            
        Returns:
            List[Dict[str, Any]]: 单词记录列表
        """
        self.log_operation("列出所有单词", limit=limit, offset=offset)
        
        query = "SELECT * FROM words LIMIT %s OFFSET %s"
        results = self.execute_query(query, (limit, offset), fetch_all=True)
        
        if results:
            results = self._parse_domain_field(results)
            self.logger.info(f"返回{len(results)}个单词")
        
        return results or []
    
    def search(self, keyword: str, field: str = "word") -> List[Dict[str, Any]]:
        """
        搜索单词
        
        Args:
            keyword (str): 搜索关键词
            field (str): 搜索字段，默认"word"
            
        Returns:
            List[Dict[str, Any]]: 匹配的单词记录列表
        """
        self.log_operation("搜索单词", keyword=keyword, field=field)
        
        # 防止SQL注入
        allowed_fields = ["word", "translation", "phonetic", "pos"]
        if field not in allowed_fields:
            field = "word"
        
        query = f"SELECT * FROM words WHERE {field} LIKE %s"
        results = self.execute_query(query, (f"%{keyword}%",), fetch_all=True)
        
        if results:
            results = self._parse_domain_field(results)
            self.logger.info(f"找到{len(results)}个匹配单词")
        
        return results or []
    
    def create(self, word: str, translation: str, phonetic: str, pos: str, tag: str, 
               total: int, spoken_ratio: float, academic_ratio: float, 
               cefr_standard: str, difficulty_level: int, dataset_type: str = None,
               definition_en: str = None, example_sentence: str = None) -> Optional[int]:
        """
        创建新词汇记录
        
        Args:
            word (str): 单词
            translation (str): 中文释义
            phonetic (str): 音标
            pos (str): 词性
            tag (str): 标签（CET4, CET6, IELTS, GRE等）
            total (int): 词频排名
            spoken_ratio (float): 口语使用频率
            academic_ratio (float): 学术使用频率
            cefr_standard (str): CEFR标准等级
            difficulty_level (int): 难度等级 1-6
            dataset_type (str): 词库体系
            definition_en (str): 英文释义
            example_sentence (str): 例句
            
        Returns:
            Optional[int]: 新创建的词汇ID
        """
        self.log_operation("创建单词", word=word, difficulty_level=difficulty_level)
        
        required_fields = ["word", "translation", "difficulty_level"]
        if not self.validate_fields({
            "word": word, "translation": translation, "difficulty_level": difficulty_level
        }, required_fields):
            return None
        
        domain_data = {"spoken_ratio": spoken_ratio, "academic_ratio": academic_ratio}
        domain_json = json.dumps(domain_data, ensure_ascii=False)

        query = """
        INSERT INTO words (word, translation, definition_en, phonetic, pos, example_sentence,
            tag, frequency_rank, cefr_standard, difficulty_level, domain, dataset_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        params = (word, translation, definition_en, phonetic, pos, example_sentence,
                 tag, total, cefr_standard, difficulty_level, domain_json, dataset_type)
        
        word_id = self.execute_insert(query, params)
        if word_id:
            self.logger.info(f"成功创建单词，ID={word_id}")
        else:
            self.logger.error("创建单词失败")
        
        return word_id
    
    def read(self, word_id: int) -> Optional[Dict[str, Any]]:
        """
        根据ID读取单词（带缓存）

        Args:
            word_id (int): 单词ID

        Returns:
            Optional[Dict[str, Any]]: 单词信息，如果不存在返回None
        """
        # 尝试从缓存获取
        cache_key = make_word_key(word_id)
        cached = word_cache.get(cache_key)
        if cached is not None:
            return cached

        self.log_operation("读取单词", word_id=word_id)

        query = "SELECT * FROM words WHERE id = %s"
        result = self.execute_query(query, (word_id,), fetch_one=True)

        if result:
            result = self._parse_domain_field([result])[0]
            self.logger.info("找到单词")
            # 缓存结果
            word_cache.set(cache_key, result)
        else:
            self.logger.info("单词不存在")

        return result
    
    def update(self, word_id: int, **kwargs) -> int:
        """
        更新单词（同时更新缓存）

        Args:
            word_id (int): 单词ID
            **kwargs: 要更新的字段和值

        Returns:
            int: 受影响的行数
        """
        self.log_operation("更新单词", word_id=word_id, kwargs=kwargs)

        if not kwargs:
            self.logger.warning("没有要更新的字段")
            return 0

        # 过滤允许更新的字段
        allowed_fields = ['word', 'translation', 'difficulty_level', 'frequency_rank',
                         'domain', 'phonetic', 'pos', 'tag', 'cefr_standard',
                         'definition_en', 'example_sentence', 'dataset_type']

        fields = {}
        for field, value in kwargs.items():
            if field in allowed_fields:
                if field == 'domain' and isinstance(value, dict):
                    value = json.dumps(value, ensure_ascii=False)
                fields[field] = value

        if not fields:
            self.logger.warning("没有有效的更新字段")
            return 0

        query, params = self.build_update_query(fields, "id = %s")
        params = params + (word_id,)

        affected_rows = self.execute_update(query, params)
        self.logger.info(f"更新了{affected_rows}行")

        # 使缓存失效
        if affected_rows > 0:
            word_cache.delete(make_word_key(word_id))
            # 清除列表缓存（因为列表数据可能变化）
            word_list_cache.clear()

        return affected_rows
    
    def delete(self, word_id: int) -> int:
        """
        删除单词
        
        Args:
            word_id (int): 单词ID
            
        Returns:
            int: 受影响的行数
        """
        self.log_operation("删除单词", word_id=word_id)
        
        query = "DELETE FROM words WHERE id = %s"
        affected_rows = self.execute_update(query, (word_id,))
        
        self.logger.info(f"删除了{affected_rows}行")
        return affected_rows
    
    def get_by_difficulty(self, difficulty_level: int, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        根据难度等级获取单词（带缓存）

        Args:
            difficulty_level (int): 难度等级（1-6）
            limit (Optional[int]): 限制返回数量
            offset (int): 偏移量

        Returns:
            List[Dict[str, Any]]: 指定难度等级的单词记录列表
        """
        # 尝试从缓存获取
        cache_key = make_word_list_key(difficulty=difficulty_level, limit=limit, offset=offset)
        cached = word_list_cache.get(cache_key)
        if cached is not None:
            return cached

        self.log_operation("根据难度获取单词", difficulty_level=difficulty_level, limit=limit, offset=offset)

        query = "SELECT * FROM words WHERE difficulty_level = %s"
        params = [difficulty_level]

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        if offset > 0:
            query += " OFFSET %s"
            params.append(offset)

        results = self.execute_query(query, tuple(params), fetch_all=True)

        if results:
            results = self._parse_domain_field(results)
            self.logger.info(f"找到{len(results)}个难度{difficulty_level}的单词")
            # 缓存结果
            word_list_cache.set(cache_key, results)

        return results or []

    def get_by_dataset_type(self, dataset_type: str, limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        根据词库类型获取单词（带缓存）

        Args:
            dataset_type (str): 词库类型（cet4, cet6, toefl, ielts等）
            limit (Optional[int]): 限制返回数量
            offset (int): 偏移量

        Returns:
            List[Dict[str, Any]]: 指定词库类型的单词记录列表
        """
        # 尝试从缓存获取
        cache_key = make_word_list_key(dataset_type=dataset_type, limit=limit, offset=offset)
        cached = word_list_cache.get(cache_key)
        if cached is not None:
            return cached

        self.log_operation("根据词库类型获取单词", dataset_type=dataset_type, limit=limit, offset=offset)

        query = "SELECT * FROM words WHERE dataset_type = %s ORDER BY frequency_rank ASC"
        params = [dataset_type]

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        if offset > 0:
            query += " OFFSET %s"
            params.append(offset)

        results = self.execute_query(query, tuple(params), fetch_all=True)

        if results:
            results = self._parse_domain_field(results)
            self.logger.info(f"找到{len(results)}个{dataset_type}词库的单词")
            # 缓存结果
            word_list_cache.set(cache_key, results)

        return results or []

    def get_by_dataset_and_difficulty(self, dataset_type: str, difficulty_level: int,
                                       limit: Optional[int] = None, offset: int = 0) -> List[Dict[str, Any]]:
        """
        根据词库类型和难度等级获取单词

        Args:
            dataset_type (str): 词库类型
            difficulty_level (int): 难度等级（1-6）
            limit (Optional[int]): 限制返回数量
            offset (int): 偏移量

        Returns:
            List[Dict[str, Any]]: 符合条件的单词记录列表
        """
        self.log_operation("根据词库和难度获取单词", dataset_type=dataset_type,
                          difficulty_level=difficulty_level, limit=limit)

        query = "SELECT * FROM words WHERE dataset_type = %s AND difficulty_level = %s ORDER BY frequency_rank ASC"
        params = [dataset_type, difficulty_level]

        if limit is not None:
            query += " LIMIT %s"
            params.append(limit)

        if offset > 0:
            query += " OFFSET %s"
            params.append(offset)

        results = self.execute_query(query, tuple(params), fetch_all=True)

        if results:
            results = self._parse_domain_field(results)
            self.logger.info(f"找到{len(results)}个符合条件的单词")

        return results or []

    def count_by_dataset(self, dataset_type: str) -> int:
        """
        统计指定词库类型的单词数量

        Args:
            dataset_type (str): 词库类型

        Returns:
            int: 单词数量
        """
        query = "SELECT COUNT(*) as cnt FROM words WHERE dataset_type = %s"
        result = self.execute_query(query, (dataset_type,), fetch_one=True)
        return result.get('cnt', 0) if result else 0

    def get_by_ids(self, word_ids: List[int]) -> List[Dict[str, Any]]:
        """
        批量获取单词（解决N+1查询问题）

        Args:
            word_ids (List[int]): 单词ID列表

        Returns:
            List[Dict[str, Any]]: 单词列表
        """
        if not word_ids:
            return []

        # 尝试从缓存获取
        results = []
        uncached_ids = []
        id_to_key = {}

        for wid in word_ids:
            key = make_word_key(wid)
            id_to_key[wid] = key
            cached = word_cache.get(key)
            if cached is not None:
                results.append(cached)
            else:
                uncached_ids.append(wid)

        # 批量查询未缓存的单词
        if uncached_ids:
            placeholders = ','.join(['%s'] * len(uncached_ids))
            query = f"SELECT * FROM words WHERE id IN ({placeholders})"
            db_results = self.execute_query(query, tuple(uncached_ids), fetch_all=True)

            if db_results:
                db_results = self._parse_domain_field(db_results)
                for word in db_results:
                    # 缓存结果
                    word_cache.set(id_to_key[word['id']], word)
                    results.append(word)

        # 按原始顺序返回
        id_to_word = {w['id']: w for w in results}
        return [id_to_word[wid] for wid in word_ids if wid in id_to_word]

    def get_random_words(self, exclude_ids: List[int] = None, limit: int = 100,
                        difficulty_range: tuple = (1, 6)) -> List[Dict[str, Any]]:
        """
        获取随机单词（用于生成错误选项等）

        Args:
            exclude_ids (List[int]): 要排除的单词ID
            limit (int): 数量限制
            difficulty_range (tuple): 难度范围 (min, max)

        Returns:
            List[Dict[str, Any]]: 随机单词列表
        """
        query = "SELECT * FROM words WHERE difficulty_level BETWEEN %s AND %s"
        params = [difficulty_range[0], difficulty_range[1]]

        if exclude_ids:
            placeholders = ','.join(['%s'] * len(exclude_ids))
            query += f" AND id NOT IN ({placeholders})"
            params.extend(exclude_ids)

        query += " ORDER BY RAND() LIMIT %s"
        params.append(limit)

        results = self.execute_query(query, tuple(params), fetch_all=True)

        if results:
            results = self._parse_domain_field(results)

        return results or []


def main():
    """
    测试函数
    演示词汇表CRUD工具的基本用法
    """
    crud = WordsCRUD()
    
    print("=== 测试词汇表CRUD ===")
    
    # 列出前5个单词
    words = crud.list_all(limit=5)
    print(f"前5个单词:")
    for word in words:
        word_id = word["id"]
        word_text = word["word"]
        translation = word["translation"][:30]
        print(f"  {word_id}: {word_text} - {translation}...")
    
    # 搜索测试
    search_results = crud.search("test")
    print(f"搜索 test 的结果: {len(search_results)} 个")
    
    crud.close()

if __name__ == "__main__":
    main()
