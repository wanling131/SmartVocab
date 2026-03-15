"""
智能推荐算法模块
基于用户画像和学习历史的单词推荐
"""

# 导入配置常量
from config import LEARNING_PARAMS

from tools.learning_records_crud import LearningRecordsCRUD
from tools.words_crud import WordsCRUD
from tools.recommendations_crud import RecommendationsCRUD
from datetime import datetime, timedelta
import random
import math
import os

# 尝试导入深度学习推荐器
try:
    from .deep_learning_recommender import DeepLearningRecommendationEngine
    DEEP_LEARNING_AVAILABLE = True
except ImportError:
    DEEP_LEARNING_AVAILABLE = False
    print("深度学习推荐器不可用，将使用传统推荐算法")

class RecommendationEngine:
    """
    推荐引擎类
    基于多种推荐算法为用户推荐合适的单词
    """
    
    def __init__(self):
        """
        初始化推荐引擎
        """
        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()
        self.recommendations_crud = RecommendationsCRUD()
        
        # 推荐算法权重
        self.weights = {
            'difficulty_based': 0.25,      # 基于难度的推荐
            'frequency_based': 0.2,        # 基于词频的推荐
            'learning_history': 0.2,       # 基于学习历史的推荐
            'deep_learning': 0.25,         # 深度学习推荐
            'random_exploration': 0.1      # 随机探索
        }
        
        # 初始化深度学习推荐器
        self.deep_learning_recommender = None
        if DEEP_LEARNING_AVAILABLE:
            try:
                self.deep_learning_recommender = DeepLearningRecommendationEngine()
                # 只在第一次初始化时打印成功信息
                if not hasattr(RecommendationEngine, '_dl_initialized'):
                    print("深度学习推荐器初始化成功")
                    RecommendationEngine._dl_initialized = True
            except Exception as e:
                print(f"深度学习推荐器初始化失败: {str(e)}")
                self.deep_learning_recommender = None
    
    def get_recommendations(self, user_id, limit=LEARNING_PARAMS["default_recommendation_limit"], algorithm="mixed"):
        """
        获取用户推荐单词
        
        Args:
            user_id (int): 用户ID
            limit (int): 推荐数量
            algorithm (str): 推荐算法类型 ("mixed", "difficulty", "frequency", "history", "random")
            
        Returns:
            list: 推荐单词列表
        """
        # 检查用户特定模型
        if self.deep_learning_recommender:
            user_model_path = f"models/deep_learning_recommender_user_{user_id}.pth"
            if os.path.exists(user_model_path):
                self.deep_learning_recommender._try_load_model(user_id)
        
        # 获取用户学习记录
        user_records = self.learning_records_crud.get_by_user(user_id)
        learned_word_ids = {record['word_id'] for record in user_records}
        
        # 根据算法类型选择推荐策略
        if algorithm == "mixed":
            recommendations = self._get_mixed_recommendations(user_id, learned_word_ids, limit)
        elif algorithm == "deep_learning":
            recommendations = self._get_deep_learning_recommendations(user_id, learned_word_ids, limit)
        elif algorithm == "difficulty":
            recommendations = self._get_difficulty_based_recommendations(user_id, learned_word_ids, limit)
        elif algorithm == "frequency":
            recommendations = self._get_frequency_based_recommendations(user_id, learned_word_ids, limit)
        elif algorithm == "history":
            recommendations = self._get_history_based_recommendations(user_id, learned_word_ids, limit)
        elif algorithm == "random":
            recommendations = self._get_random_recommendations(user_id, learned_word_ids, limit)
        else:
            recommendations = self._get_mixed_recommendations(user_id, learned_word_ids, limit)
        
        # 保存推荐记录
        self._save_recommendations(user_id, recommendations)
        
        return recommendations
    
    def _get_mixed_recommendations(self, user_id, learned_word_ids, limit):
        """
        混合推荐算法
        
        Args:
            user_id (int): 用户ID
            learned_word_ids (set): 已学单词ID集合
            limit (int): 推荐数量
            
        Returns:
            list: 推荐单词列表
        """
        # 获取各种推荐结果
        difficulty_recs = self._get_difficulty_based_recommendations(user_id, learned_word_ids, limit * 2)
        frequency_recs = self._get_frequency_based_recommendations(user_id, learned_word_ids, limit * 2)
        history_recs = self._get_history_based_recommendations(user_id, learned_word_ids, limit * 2)
        deep_learning_recs = self._get_deep_learning_recommendations(user_id, learned_word_ids, limit * 2)
        random_recs = self._get_random_recommendations(user_id, learned_word_ids, limit)
        
        # 计算综合推荐分数
        all_candidates = {}
        
        # 难度推荐
        for word in difficulty_recs:
            word_id = word['id']
            if word_id not in all_candidates:
                all_candidates[word_id] = {'word': word, 'score': 0}
            all_candidates[word_id]['score'] += self.weights['difficulty_based'] * word.get('recommendation_score', 0.5)
        
        # 词频推荐
        for word in frequency_recs:
            word_id = word['id']
            if word_id not in all_candidates:
                all_candidates[word_id] = {'word': word, 'score': 0}
            all_candidates[word_id]['score'] += self.weights['frequency_based'] * word.get('recommendation_score', 0.5)
        
        # 历史推荐
        for word in history_recs:
            word_id = word['id']
            if word_id not in all_candidates:
                all_candidates[word_id] = {'word': word, 'score': 0}
            all_candidates[word_id]['score'] += self.weights['learning_history'] * word.get('recommendation_score', 0.5)
        
        # 深度学习推荐
        for word in deep_learning_recs:
            word_id = word['id']
            if word_id not in all_candidates:
                all_candidates[word_id] = {'word': word, 'score': 0}
            all_candidates[word_id]['score'] += self.weights['deep_learning'] * word.get('recommendation_score', 0.5)
        
        # 随机探索
        for word in random_recs:
            word_id = word['id']
            if word_id not in all_candidates:
                all_candidates[word_id] = {'word': word, 'score': 0}
            all_candidates[word_id]['score'] += self.weights['random_exploration'] * word.get('recommendation_score', 0.5)
        
        # 按分数排序并返回前limit个
        sorted_candidates = sorted(all_candidates.values(), key=lambda x: x['score'], reverse=True)
        recommendations = [candidate['word'] for candidate in sorted_candidates[:limit]]
        
        # 为每个推荐添加理由和算法类型
        for rec in recommendations:
            # 根据推荐来源确定算法类型
            algorithm_type = self._determine_algorithm_type(rec, difficulty_recs, frequency_recs, history_recs, deep_learning_recs, random_recs)
            rec['algorithm_type'] = algorithm_type
            rec['reason'] = self._generate_recommendation_reason(rec, algorithm_type)
        
        return recommendations
    
    def _determine_algorithm_type(self, recommendation, difficulty_recs, frequency_recs, history_recs, deep_learning_recs, random_recs):
        """
        根据推荐来源确定算法类型
        
        Args:
            recommendation (dict): 推荐结果
            difficulty_recs (list): 难度推荐结果
            frequency_recs (list): 频率推荐结果
            history_recs (list): 历史推荐结果
            deep_learning_recs (list): 深度学习推荐结果
            random_recs (list): 随机推荐结果
            
        Returns:
            str: 算法类型
        """
        word_id = recommendation['id']
        
        # 检查推荐来源，按优先级排序
        if any(word['id'] == word_id for word in deep_learning_recs):
            return 'deep_learning'
        elif any(word['id'] == word_id for word in difficulty_recs):
            return 'difficulty_based'
        elif any(word['id'] == word_id for word in frequency_recs):
            return 'frequency_based'
        elif any(word['id'] == word_id for word in history_recs):
            return 'collaborative'
        elif any(word['id'] == word_id for word in random_recs):
            return 'random'
        else:
            return 'mixed'
    
    def _get_deep_learning_recommendations(self, user_id, learned_word_ids, limit):
        """
        深度学习推荐算法
        
        Args:
            user_id (int): 用户ID
            learned_word_ids (set): 已学单词ID集合
            limit (int): 推荐数量
            
        Returns:
            list: 推荐单词列表
        """
        if not self.deep_learning_recommender:
            # 如果深度学习推荐器不可用，使用传统推荐
            return self._get_difficulty_based_recommendations(user_id, learned_word_ids, limit)
        
        try:
            # 检查并训练用户特定模型
            if self.deep_learning_recommender:
                self.deep_learning_recommender.check_and_train_model(user_id)
            
            # 尝试为特定用户加载模型
            if hasattr(self.deep_learning_recommender, '_try_load_model'):
                self.deep_learning_recommender._try_load_model(user_id)
            
            # 如果模型未训练，尝试为当前用户训练
            if not self.deep_learning_recommender.is_trained:
                print(f"为用户 {user_id} 训练深度学习模型...")
                success = self.deep_learning_recommender.train_model_for_user(user_id)
                if not success:
                    print("深度学习模型训练失败，使用传统推荐")
                    return self._get_difficulty_based_recommendations(user_id, learned_word_ids, limit)
            
            # 使用深度学习模型获取推荐
            recommendations = self.deep_learning_recommender.get_deep_learning_recommendations(user_id, limit)
            
            # 添加算法类型标识和推荐理由
            for rec in recommendations:
                rec['algorithm_type'] = 'deep_learning'
                rec['reason'] = self._generate_recommendation_reason(rec, 'deep_learning')
            
            return recommendations
        except Exception as e:
            print(f"深度学习推荐失败: {str(e)}")
            # 降级到传统推荐
            return self._get_difficulty_based_recommendations(user_id, learned_word_ids, limit)
    
    def _generate_recommendation_reason(self, recommendation, algorithm_type):
        """
        生成推荐理由
        
        Args:
            recommendation (dict): 推荐结果
            algorithm_type (str): 算法类型
            
        Returns:
            str: 推荐理由
        """
        try:
            if algorithm_type == 'deep_learning':
                # 基于深度学习模型的推荐理由
                mastery_level = recommendation.get('mastery_level', 0)
                difficulty = recommendation.get('difficulty_level', 3)
                frequency_rank = recommendation.get('frequency_rank', 1000)
                tag = recommendation.get('tag', '')
                
                # 根据考试标签选择理由
                if '四级' in tag or '六级' in tag:
                    return "AI推荐：四六级必备词汇"
                elif '考研' in tag:
                    return "AI推荐：考研核心词汇"
                elif '雅思' in tag or '托福' in tag:
                    return "AI推荐：留学考试词汇"
                elif 'GRE' in tag:
                    return "AI推荐：GRE学术词汇"
                
                # 根据词频选择理由
                elif frequency_rank <= LEARNING_PARAMS["frequency_threshold"]:
                    return "AI推荐：高频核心词汇"
                elif frequency_rank <= 1000:
                    return "AI推荐：常用实用词汇"
                
                # 根据掌握程度选择理由
                elif mastery_level < 0.3:
                    return "AI预测：适合您当前水平"
                elif mastery_level < 0.6:
                    return "AI推荐：巩固学习效果"
                else:
                    return "AI建议：挑战更高难度"
                    
            elif algorithm_type == 'difficulty_based':
                # 基于难度的推荐理由
                difficulty = recommendation.get('difficulty_level', 3)
                frequency_rank = recommendation.get('frequency_rank', 1000)
                
                # 结合词频和难度生成更丰富的理由
                if difficulty <= 2:
                    if frequency_rank <= 500:
                        return "核心基础：高频入门词汇"
                    elif frequency_rank <= 1000:
                        return "基础词汇：实用性强"
                    else:
                        return "入门词汇：轻松掌握"
                elif difficulty <= 4:
                    if frequency_rank <= 500:
                        return "进阶核心：高频进阶词汇"
                    elif frequency_rank <= 1000:
                        return "进阶词汇：稳步提升"
                    else:
                        return "中级词汇：拓展词汇量"
                else:
                    if frequency_rank <= 500:
                        return "高级核心：高频高级词汇"
                    elif frequency_rank <= 1000:
                        return "高级词汇：挑战自我"
                    else:
                        return "专业词汇：学术表达"
                    
            elif algorithm_type == 'frequency_based':
                # 基于频率的推荐理由
                frequency_rank = recommendation.get('frequency_rank', 1000)
                if frequency_rank <= LEARNING_PARAMS["frequency_threshold"]:
                    return "高频词汇：使用频繁"
                elif frequency_rank <= 1000:
                    return "常用词汇：实用性强"
                else:
                    return "扩展词汇：丰富表达"
                    
            elif algorithm_type == 'collaborative':
                # 基于协同过滤的推荐理由
                return "相似用户：学习偏好匹配"
                
            elif algorithm_type == 'random':
                # 随机探索的推荐理由
                difficulty = recommendation.get('difficulty_level', 3)
                if difficulty <= 2:
                    return "随机探索：发现新词汇"
                elif difficulty <= 4:
                    return "随机推荐：拓展词汇量"
                else:
                    return "随机挑战：突破舒适区"
                
            elif algorithm_type == 'mixed':
                # 混合推荐：根据单词特征智能选择理由
                difficulty = recommendation.get('difficulty_level', 3)
                frequency_rank = recommendation.get('frequency_rank', 1000)
                domain = recommendation.get('domain', [])
                tag = recommendation.get('tag', '')
                
                # 根据考试标签选择理由
                if '四级' in tag or '六级' in tag:
                    return "考试词汇：四六级必备"
                elif '考研' in tag:
                    return "考研词汇：学术进阶"
                elif '雅思' in tag or '托福' in tag:
                    return "留学词汇：国际考试"
                elif 'GRE' in tag:
                    return "GRE词汇：学术精英"
                
                # 根据使用领域选择理由
                elif 'spoken' in domain:
                    return "口语词汇：日常交流"
                elif 'academic' in domain:
                    return "学术词汇：专业表达"
                elif 'business' in domain:
                    return "商务词汇：职场必备"
                
                # 根据词频选择理由
                elif frequency_rank <= LEARNING_PARAMS["frequency_threshold"]:
                    return "核心词汇：使用频率最高"
                elif frequency_rank <= 1000:
                    return "重要词汇：实用性强"
                
                # 根据难度选择理由
                elif difficulty <= 2:
                    return "入门词汇：轻松掌握"
                elif difficulty <= 4:
                    return "进阶词汇：稳步提升"
                else:
                    return "高级词汇：挑战自我"
                
            else:
                return "智能推荐：个性化学习"
                
        except Exception as e:
            print(f"生成推荐理由失败: {str(e)}")
            return "智能推荐"
    
    def _get_difficulty_based_recommendations(self, user_id, learned_word_ids, limit):
        """
        基于难度的推荐
        
        Args:
            user_id (int): 用户ID
            learned_word_ids (set): 已学单词ID集合
            limit (int): 推荐数量
            
        Returns:
            list: 推荐单词列表
        """
        # 获取用户学习进度
        user_records = self.learning_records_crud.get_by_user(user_id)
        if not user_records:
            # 新用户，推荐简单单词
            target_difficulty = 1
        else:
            # 根据用户平均掌握程度推荐合适难度的单词
            avg_mastery = sum(record['mastery_level'] for record in user_records) / len(user_records)
            target_difficulty = min(6, max(1, int(avg_mastery * 6) + 1))
        
        # 获取指定难度的单词
        all_words = self.words_crud.list_all(limit=500)
        difficulty_words = [word for word in all_words 
                           if word['difficulty_level'] == target_difficulty 
                           and word['id'] not in learned_word_ids]
        
        # 随机选择
        selected_words = random.sample(difficulty_words, min(limit, len(difficulty_words)))
        
        # 添加推荐分数
        for word in selected_words:
            word['recommendation_score'] = 0.8  # 难度匹配度高
        
        return selected_words
    
    def _get_frequency_based_recommendations(self, user_id, learned_word_ids, limit):
        """
        基于词频的推荐
        
        Args:
            user_id (int): 用户ID
            learned_word_ids (set): 已学单词ID集合
            limit (int): 推荐数量
            
        Returns:
            list: 推荐单词列表
        """
        # 获取用户学习进度，确定合适难度范围
        user_records = self.learning_records_crud.get_by_user(user_id)
        if not user_records:
            # 新用户，推荐简单单词
            min_difficulty, max_difficulty = 1, 2
        else:
            # 根据用户平均掌握程度推荐合适难度的单词
            avg_mastery = sum(record['mastery_level'] for record in user_records) / len(user_records)
            base_difficulty = min(6, max(1, int(avg_mastery * 6) + 1))
            min_difficulty = max(1, base_difficulty - 1)
            max_difficulty = min(6, base_difficulty + 1)
        
        # 获取指定难度范围内的高频单词
        all_words = self.words_crud.list_all(limit=500)
        frequency_words = [word for word in all_words 
                          if word['id'] not in learned_word_ids
                          and min_difficulty <= word['difficulty_level'] <= max_difficulty]
        
        # 按词频排序（frequency_rank越小越高频）
        frequency_words.sort(key=lambda x: x['frequency_rank'])
        
        # 选择前limit个
        selected_words = frequency_words[:limit]
        
        # 添加推荐分数
        for i, word in enumerate(selected_words):
            # 词频越高，分数越高
            word['recommendation_score'] = max(0.1, 1.0 - (i / len(selected_words)) * 0.5)
        
        return selected_words
    
    def _get_history_based_recommendations(self, user_id, learned_word_ids, limit):
        """
        基于学习历史的推荐
        
        Args:
            user_id (int): 用户ID
            learned_word_ids (set): 已学单词ID集合
            limit (int): 推荐数量
            
        Returns:
            list: 推荐单词列表
        """
        # 获取用户学习记录
        user_records = self.learning_records_crud.get_by_user(user_id)
        if not user_records:
            return []
        
        # 分析用户学习偏好
        user_preferences = self._analyze_user_preferences(user_records)
        
        # 根据偏好推荐相似单词
        all_words = self.words_crud.list_all(limit=500)
        candidate_words = [word for word in all_words if word['id'] not in learned_word_ids]
        
        # 计算相似度分数
        for word in candidate_words:
            similarity_score = self._calculate_word_similarity(word, user_preferences)
            word['recommendation_score'] = similarity_score
        
        # 按相似度排序
        candidate_words.sort(key=lambda x: x['recommendation_score'], reverse=True)
        
        return candidate_words[:limit]
    
    def _get_random_recommendations(self, user_id, learned_word_ids, limit):
        """
        随机推荐（用于探索）
        
        Args:
            user_id (int): 用户ID
            learned_word_ids (set): 已学单词ID集合
            limit (int): 推荐数量
            
        Returns:
            list: 推荐单词列表
        """
        # 获取用户学习进度，确定合适难度范围
        user_records = self.learning_records_crud.get_by_user(user_id)
        if not user_records:
            # 新用户，推荐简单单词
            min_difficulty, max_difficulty = 1, 2
        else:
            # 根据用户平均掌握程度推荐合适难度的单词
            avg_mastery = sum(record['mastery_level'] for record in user_records) / len(user_records)
            base_difficulty = min(6, max(1, int(avg_mastery * 6) + 1))
            min_difficulty = max(1, base_difficulty - 1)
            max_difficulty = min(6, base_difficulty + 1)
        
        # 获取指定难度范围内的未学单词
        all_words = self.words_crud.list_all(limit=500)
        unlearned_words = [word for word in all_words 
                          if word['id'] not in learned_word_ids
                          and min_difficulty <= word['difficulty_level'] <= max_difficulty]
        
        # 随机选择
        selected_words = random.sample(unlearned_words, min(limit, len(unlearned_words)))
        
        # 添加推荐分数
        for word in selected_words:
            word['recommendation_score'] = random.uniform(0.1, 0.5)  # 随机分数
        
        return selected_words
    
    def _analyze_user_preferences(self, user_records):
        """
        分析用户学习偏好
        
        Args:
            user_records (list): 用户学习记录
            
        Returns:
            dict: 用户偏好信息
        """
        preferences = {
            'preferred_difficulty': [],
            'preferred_pos': [],
            'preferred_tags': [],
            'learning_speed': 0.0
        }
        
        if not user_records:
            return preferences
        
        # 分析难度偏好
        difficulty_counts = {}
        for record in user_records:
            # 这里需要根据word_id获取单词信息
            # 简化处理，假设有difficulty_level字段
            difficulty = record.get('difficulty_level', 3)
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1
        
        preferences['preferred_difficulty'] = max(difficulty_counts.keys(), key=difficulty_counts.get) if difficulty_counts else 3
        
        # 分析学习速度
        total_reviews = sum(record['review_count'] for record in user_records)
        preferences['learning_speed'] = total_reviews / len(user_records) if user_records else 1.0
        
        return preferences
    
    def _calculate_word_similarity(self, word, user_preferences):
        """
        计算单词与用户偏好的相似度
        
        Args:
            word (dict): 单词信息
            user_preferences (dict): 用户偏好
            
        Returns:
            float: 相似度分数
        """
        score = 0.0
        
        # 难度匹配
        if word['difficulty_level'] == user_preferences['preferred_difficulty']:
            score += 0.4
        
        # 词频权重
        if word['frequency_rank'] < 1000:  # 高频词
            score += 0.3
        
        # 随机因素
        score += random.uniform(0, 0.3)
        
        return min(1.0, score)
    
    def _save_recommendations(self, user_id, recommendations):
        """
        保存推荐记录
        
        Args:
            user_id (int): 用户ID
            recommendations (list): 推荐单词列表
        """
        for word in recommendations:
            self.recommendations_crud.create(
                user_id=user_id,
                word_id=word['id'],
                recommendation_score=word.get('recommendation_score', 0.5),
                recommendation_type=word.get('algorithm_type', 'mixed'),
                reason=word.get('reason', ''),
                created_at=datetime.now()
            )
    
    def update_user_profile(self, user_id, learning_data):
        """
        更新用户画像
        
        Args:
            user_id (int): 用户ID
            learning_data (dict): 学习数据
            
        Returns:
            bool: 更新结果
        """
        # 这里可以实现用户画像的更新逻辑
        # 例如：更新用户的学习偏好、难度偏好等
        return True
    
    def calculate_recommendation_score(self, user_id, word_id):
        """
        计算推荐分数
        
        Args:
            user_id (int): 用户ID
            word_id (int): 单词ID
            
        Returns:
            float: 推荐分数
        """
        # 获取单词信息
        word = self.words_crud.read(word_id)
        if not word:
            return 0.0
        
        # 获取用户学习记录
        user_records = self.learning_records_crud.get_by_user(user_id)
        if not user_records:
            # 新用户，基于词频推荐
            return max(0.1, 1.0 - word['frequency_rank'] / 10000)
        
        # 分析用户偏好
        user_preferences = self._analyze_user_preferences(user_records)
        
        # 计算相似度分数
        return self._calculate_word_similarity(word, user_preferences)
    
    def get_recommendation_history(self, user_id, limit=LEARNING_PARAMS["default_review_limit"]):
        """
        获取推荐历史
        
        Args:
            user_id (int): 用户ID
            limit (int): 限制数量
            
        Returns:
            list: 推荐历史列表
        """
        return self.recommendations_crud.get_by_user(user_id, limit)
    
    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass
