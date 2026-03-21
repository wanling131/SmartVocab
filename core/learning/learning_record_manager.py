"""
学习记录管理模块
负责用户学习记录的增删改查、学习进度跟踪等功能
"""

# 导入配置常量
import logging
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from config import LEARNING_PARAMS

logger = logging.getLogger(__name__)

from tools.learning_records_crud import LearningRecordsCRUD
from tools.words_crud import WordsCRUD
from datetime import datetime, timedelta
from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

class LearningRecordManager:
    """
    学习记录管理类
    负责用户学习记录的完整生命周期管理
    """
    
    def __init__(self):
        """
        初始化学习记录管理器
        """
        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()
        self.forgetting_curve_manager = ForgettingCurveManager()
    
    def create_learning_record(self, user_id, word_id, mastery_level=0.0, 
                              last_reviewed_at=None, review_count=0, 
                              is_mastered=False):
        """
        创建学习记录
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            mastery_level (float): 掌握程度 (0.0-1.0)
            last_reviewed_at (datetime): 最后复习时间
            review_count (int): 复习次数
            is_mastered (bool): 是否已掌握
            
        Returns:
            dict: 创建结果
        """
        # 检查用户是否已有该单词的学习记录
        existing_records = self.learning_records_crud.search_by_user_word(user_id, word_id)
        if existing_records:
            return {"success": False, "message": "该单词的学习记录已存在"}
        
        # 设置默认最后复习时间为当前时间
        if last_reviewed_at is None:
            last_reviewed_at = datetime.now()
        first_learned_at = last_reviewed_at
        
        # 计算下次复习时间（记忆曲线持久化）
        next_review_at = self.forgetting_curve_manager.calculate_next_review_time(
            user_id, word_id, mastery_level, review_count
        )
        
        # 创建学习记录（含 first_learned_at、next_review_at，CRUD 内兼容旧表结构）
        record_id = self.learning_records_crud.create(
            user_id=user_id,
            word_id=word_id,
            mastery_level=mastery_level,
            last_reviewed_at=last_reviewed_at,
            review_count=review_count,
            is_mastered=is_mastered,
            first_learned_at=first_learned_at,
            next_review_at=next_review_at,
            level_gate_id=None
        )
        
        # 检查是否需要训练模型（每50个单词训练一次）
        self._check_and_train_model_if_needed(user_id)
        
        return {"success": True, "message": "学习记录创建成功", "record_id": record_id}
    
    def get_user_learning_records(self, user_id, limit=None, offset=0):
        """
        获取用户学习记录（包含单词信息）
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量
            offset (int): 偏移量
            
        Returns:
            list: 学习记录列表，包含单词信息
        """
        # 使用现有的CRUD工具获取学习记录
        records = self.learning_records_crud.get_by_user(user_id, limit, offset)
        
        if not records:
            return []
        
        # 后处理：为每个记录添加单词信息
        enriched_records = []
        for record in records:
            # 获取单词详细信息
            word_info = self.words_crud.read(record['word_id'])
            
            if word_info:
                # 合并学习记录和单词信息
                enriched_record = {
                    **record,  # 包含所有学习记录字段
                    'word': word_info.get('word', ''),
                    'translation': word_info.get('translation', ''),
                    'phonetic': word_info.get('phonetic', ''),
                    'pos': word_info.get('pos', ''),
                    'difficulty_level': word_info.get('difficulty_level', 1),
                    'is_correct': 1 if record['mastery_level'] >= 0.1 else 0,  # 基于掌握程度判断，降低阈值
                    'created_at': record['last_reviewed_at']  # 使用最后复习时间作为创建时间
                }
                enriched_records.append(enriched_record)
            else:
                # 如果单词不存在，仍然添加记录但标记为未知
                enriched_record = {
                    **record,
                    'word': f"未知单词(ID:{record['word_id']})",
                    'translation': '单词信息缺失',
                    'phonetic': '',
                    'pos': '',
                    'difficulty_level': 1,
                    'is_correct': 1 if record['mastery_level'] >= 0.1 else 0,
                    'created_at': record['last_reviewed_at']
                }
                enriched_records.append(enriched_record)
        
        # print(f"DEBUG LearningRecordManager.get_user_learning_records: 返回{len(enriched_records)}条增强记录")
        return enriched_records
    
    def get_word_learning_record(self, user_id, word_id):
        """
        获取特定单词的学习记录
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            
        Returns:
            dict: 学习记录，如果不存在返回None
        """
        records = self.learning_records_crud.search_by_user_word(user_id, word_id)
        return records[0] if records else None
    
    def update_mastery_level(self, record_id, mastery_level, is_correct=True, question_type="translation"):
        """
        更新掌握程度
        
        Args:
            record_id (int): 记录ID
            mastery_level (float): 掌握程度 (0.0-1.0)
            is_correct (bool): 本次答题是否正确
            question_type (str): 题目类型 ("choice", "translation", "spelling")
            
        Returns:
            dict: 更新结果
        """
        # 获取当前记录
        record = self.learning_records_crud.read(record_id)
        if not record:
            return {"success": False, "message": "学习记录不存在"}
        
        # 根据题目类型和答题结果计算新的掌握程度
        new_mastery = self._calculate_mastery_by_question_type(
            record['mastery_level'], is_correct, question_type
        )
        
        # 更新复习次数和最后复习时间
        new_review_count = record['review_count'] + 1
        new_is_learned = new_mastery >= 0.8  # 掌握程度达到80%认为已学会
        
        # 计算并持久化下次复习时间（记忆曲线）
        next_review_at = self.forgetting_curve_manager.calculate_next_review_time(
            record['user_id'], record['word_id'], new_mastery, new_review_count
        )
        
        # 更新记录（含 next_review_at）
        affected_rows = self.learning_records_crud.update(
            record_id,
            mastery_level=new_mastery,
            review_count=new_review_count,
            last_reviewed_at=datetime.now(),
            is_mastered=new_is_learned,
            next_review_at=next_review_at
        )
        
        return {
            "success": affected_rows > 0,
            "message": "掌握程度更新成功" if affected_rows > 0 else "更新失败",
            "new_mastery_level": new_mastery,
            "is_mastered": new_is_learned
        }
    
    def _calculate_mastery_by_question_type(self, current_mastery, is_correct, question_type):
        """
        根据题目类型计算新的掌握程度
        
        Args:
            current_mastery (float): 当前掌握程度
            is_correct (bool): 答题是否正确
            question_type (str): 题目类型
            
        Returns:
            float: 新的掌握程度
        """
        if is_correct:
            # 答对了，根据题目类型增加掌握程度
            if question_type == "choice":
                increase = 0.2  # 选择题相对简单
            elif question_type == "translation":
                increase = 0.3  # 翻译题中等难度
            elif question_type == "spelling":
                increase = 0.4  # 拼写题最难
            else:
                increase = 0.2  # 默认值，保持向后兼容
            
            new_mastery = min(1.0, current_mastery + increase)
        else:
            # 答错了，统一减少掌握程度
            decrease = 0.1
            new_mastery = max(0.0, current_mastery - decrease)
        
        return new_mastery
    
    def get_learning_progress(self, user_id):
        """
        获取学习进度
        
        Args:
            user_id (int): 用户ID
            
        Returns:
            dict: 学习进度信息
        """
        # 获取用户所有学习记录
        all_records = self.learning_records_crud.get_by_user(user_id)
        
        if not all_records:
            return {
                "total_words": 0,
                "learned_words": 0,
                "learning_words": 0,
                "mastery_rate": 0.0,
                "total_reviews": 0,
                "average_mastery": 0.0
            }
        
        # 统计学习进度
        total_words = len(all_records)
        learned_words = sum(1 for record in all_records if record['is_mastered'])
        learning_words = total_words - learned_words
        mastery_rate = learned_words / total_words if total_words > 0 else 0.0
        total_reviews = sum(record['review_count'] for record in all_records)
        average_mastery = sum(record['mastery_level'] for record in all_records) / total_words
        
        return {
            "total_words": total_words,
            "learned_words": learned_words,
            "learning_words": learning_words,
            "mastery_rate": round(mastery_rate, 2),
            "total_reviews": total_reviews,
            "average_mastery": round(average_mastery, 2)
        }
    
    def get_words_to_review(self, user_id, limit=LEARNING_PARAMS["default_review_limit"], offset=0):
        """
        获取需要复习的单词（支持轮播）
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量，默认20个
            offset (int): 偏移量，用于轮播
            
        Returns:
            list: 需要复习的单词记录列表
        """
        # 获取用户所有学习记录
        all_records = self.learning_records_crud.get_by_user(user_id)
        
        # 筛选需要复习的记录（掌握程度小于1.0）
        now = datetime.now()
        review_records = []
        
        for record in all_records:
            if record['mastery_level'] < 1.0:  # 未完全掌握
                last_reviewed = record['last_reviewed_at']
                if isinstance(last_reviewed, str):
                    last_reviewed = datetime.fromisoformat(last_reviewed.replace('Z', '+00:00'))
                
                # 计算复习紧急程度
                if record['mastery_level'] < 0.5:
                    # 掌握程度很低，优先复习
                    urgency = 1000
                elif record['mastery_level'] < 0.8:
                    # 掌握程度中等，根据时间计算紧急程度
                    days_since_review = (now - last_reviewed).days
                    urgency = LEARNING_PARAMS["urgency_base"] + days_since_review * LEARNING_PARAMS["urgency_multiplier"]
                else:
                    # 掌握程度较高，根据时间计算紧急程度
                    days_since_review = (now - last_reviewed).days
                    urgency = days_since_review * 5
                
                record['urgency'] = urgency
                review_records.append(record)
        
        # 按紧急程度排序，最紧急的优先
        review_records.sort(key=lambda x: x['urgency'], reverse=True)
        
        # 支持轮播：从offset开始取limit个
        start_idx = offset % len(review_records) if review_records else 0
        end_idx = start_idx + limit
        
        if end_idx <= len(review_records):
            # 正常情况
            return review_records[start_idx:end_idx]
        else:
            # 需要循环取数据
            result = review_records[start_idx:]
            remaining = limit - len(result)
            if remaining > 0:
                result.extend(review_records[:remaining])
            return result
    
    def _check_and_train_model_if_needed(self, user_id):
        """
        检查是否需要训练模型（每50个单词训练一次）
        
        Args:
            user_id (int): 用户ID
        """
        try:
            # 获取用户学习记录总数
            all_records = self.learning_records_crud.get_by_user(user_id)
            total_records = len(all_records)
            
            # 检查是否是50的倍数
            if total_records > 0 and total_records % LEARNING_PARAMS["min_training_records"] == 0:
                # print(f"用户 {user_id} 已学习 {total_records} 个单词，触发模型训练...")
                
                # 导入推荐引擎并触发模型训练
                from core.recommendation.recommendation_engine import RecommendationEngine
                recommendation_engine = RecommendationEngine()
                
                if hasattr(recommendation_engine, 'deep_learning_recommender') and recommendation_engine.deep_learning_recommender:
                    success = recommendation_engine.deep_learning_recommender.check_and_train_model(user_id)
                    if success:
                        logger.info("用户 %s 的模型训练完成", user_id)
                    else:
                        logger.warning("用户 %s 的模型训练失败", user_id)
                else:
                    logger.debug("深度学习推荐器不可用")
                    
        except Exception as e:
            logger.exception("检查模型训练时出错: %s", e)
    
    def get_learning_statistics(self, user_id, days=7):
        """
        获取学习统计
        
        Args:
            user_id (int): 用户ID
            days (int): 统计天数
            
        Returns:
            dict: 学习统计数据
        """
        # 获取用户所有学习记录
        all_records = self.learning_records_crud.get_by_user(user_id)
        
        # 计算时间范围
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        # 筛选时间范围内的记录
        recent_records = []
        for record in all_records:
            last_reviewed = record['last_reviewed_at']
            if isinstance(last_reviewed, str):
                last_reviewed = datetime.fromisoformat(last_reviewed.replace('Z', '+00:00'))
            
            if start_date <= last_reviewed <= end_date:
                recent_records.append(record)
        
        # 统计学习数据
        total_reviews = sum(record['review_count'] for record in recent_records)
        new_words = len([r for r in recent_records if r['review_count'] == 1])
        learned_words = len([r for r in recent_records if r['is_mastered']])
        
        return {
            "period_days": days,
            "total_reviews": total_reviews,
            "new_words": new_words,
            "learned_words": learned_words,
            "average_reviews_per_day": round(total_reviews / days, 2)
        }
    
    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass
