"""
智能推荐算法模块（增强版 + 性能优化）
集成：协同过滤、动态权重、多样性控制、冷启动策略、实时个性化

Author: SmartVocab Team
Version: 2.1 (Performance Optimized)
"""

# 导入配置常量
import logging
import os
import random
from datetime import datetime
from typing import Dict

from config import LEARNING_PARAMS, RECOMMENDATION_CONFIG
from tools.learning_records_crud import LearningRecordsCRUD

logger = logging.getLogger(__name__)

from tools.memory_cache import make_recommendation_key, recommendation_cache
from tools.recommendations_crud import RecommendationsCRUD
from tools.words_crud import WordsCRUD

# 尝试导入深度学习推荐器
try:
    from .deep_learning_recommender import DeepLearningRecommendationEngine

    DEEP_LEARNING_AVAILABLE = True
except ImportError:
    DEEP_LEARNING_AVAILABLE = False
    logging.getLogger(__name__).warning("深度学习推荐器不可用，将使用传统推荐算法")

# 导入增强模块
try:
    from .recommendation_enhancements import (
        ColdStartHandler,
        CollaborativeFiltering,
        DiversityController,
        DynamicWeightAdjuster,
        RealtimePersonalizer,
    )

    ENHANCEMENTS_AVAILABLE = True
except ImportError as e:
    ENHANCEMENTS_AVAILABLE = False
    logging.getLogger(__name__).warning("推荐增强模块不可用: %s", e)


class RecommendationEngine:
    """
    推荐引擎类（增强版）
    基于多种推荐算法为用户推荐合适的单词
    集成协同过滤、动态权重、多样性控制、冷启动处理、实时个性化
    """

    def __init__(self):
        """
        初始化推荐引擎
        """
        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()
        self.recommendations_crud = RecommendationsCRUD()

        # 从配置文件读取基础算法权重（支持动态配置）
        config_weights = RECOMMENDATION_CONFIG.get("algorithm_weights", {})
        if config_weights:
            # 映射配置键名到内部键名
            self.base_weights = {
                "difficulty_based": config_weights.get("difficulty_based", 0.21),
                "frequency_based": config_weights.get("frequency_based", 0.17),
                "learning_history": config_weights.get("learning_history", 0.17),
                "deep_learning": config_weights.get("deep_learning", 0.25),
                "collaborative": config_weights.get("collaborative", 0.13),
                "random_exploration": config_weights.get("random_exploration", 0.07),
            }
            logger.info(f"从配置文件加载算法权重: {self.base_weights}")
        else:
            # 默认权重（总和应为1.0）
            self.base_weights = {
                "difficulty_based": 0.21,  # 基于难度的推荐
                "frequency_based": 0.17,  # 基于词频的推荐
                "learning_history": 0.17,  # 基于学习历史的推荐
                "deep_learning": 0.25,  # 深度学习推荐
                "collaborative": 0.13,  # 协同过滤推荐
                "random_exploration": 0.07,  # 随机探索
            }
            logger.info("使用默认算法权重")

        # 归一化权重（确保总和为1.0）
        total = sum(self.base_weights.values())
        if abs(total - 1.0) > 0.001:  # 如果总和不为1.0，进行归一化
            self.base_weights = {k: v / total for k, v in self.base_weights.items()}
            logger.info(f"权重已归一化，原总和: {total:.3f}")

        # 初始化深度学习推荐器
        self.deep_learning_recommender = None
        if DEEP_LEARNING_AVAILABLE:
            try:
                self.deep_learning_recommender = DeepLearningRecommendationEngine()
                if not hasattr(RecommendationEngine, "_dl_initialized"):
                    logger.info("深度学习推荐器初始化成功")
                    RecommendationEngine._dl_initialized = True
            except Exception as e:
                logger.warning("深度学习推荐器初始化失败: %s", e)
                self.deep_learning_recommender = None

        # 初始化增强模块
        self.collaborative_filter = None
        self.weight_adjuster = None
        self.diversity_controller = None
        self.cold_start_handler = None
        self.realtime_personalizer = None

        if ENHANCEMENTS_AVAILABLE:
            try:
                self.collaborative_filter = CollaborativeFiltering()
                self.weight_adjuster = DynamicWeightAdjuster()
                self.diversity_controller = DiversityController()
                self.cold_start_handler = ColdStartHandler()
                self.realtime_personalizer = RealtimePersonalizer()
                logger.info("推荐增强模块初始化成功")
            except Exception as e:
                logger.warning("推荐增强模块初始化失败: %s", e)

    def get_recommendations(
        self, user_id, limit=LEARNING_PARAMS["default_recommendation_limit"], algorithm="mixed"
    ):
        """
        获取用户推荐单词（带缓存优化）

        Args:
            user_id (int): 用户ID
            limit (int): 推荐数量
            algorithm (str): 推荐算法类型

        Returns:
            list: 推荐单词列表
        """
        # 尝试从缓存获取
        cache_key = make_recommendation_key(user_id, algorithm, limit)
        cached = recommendation_cache.get(cache_key)
        if cached is not None:
            logger.debug("从缓存获取推荐结果: user_id=%s", user_id)
            return cached

        # 检查用户特定模型
        if self.deep_learning_recommender:
            user_model_path = f"models/deep_learning_recommender_user_{user_id}.pth"
            if os.path.exists(user_model_path):
                self.deep_learning_recommender._try_load_model(user_id)

        # 获取用户学习记录
        user_records = self.learning_records_crud.get_by_user(user_id)
        learned_word_ids = {record["word_id"] for record in user_records}
        record_count = len(user_records)

        # 冷启动检测
        if self.cold_start_handler and self.cold_start_handler.is_cold_start_user(user_id):
            logger.info("用户 %s 为冷启动用户，使用冷启动策略", user_id)
            cold_start_recs = self.cold_start_handler.get_cold_start_recommendations(user_id, limit)
            if cold_start_recs:
                recommendation_cache.set(cache_key, cold_start_recs)
                return cold_start_recs

        # 获取动态权重
        weights = self._get_dynamic_weights(user_id, record_count)

        # 根据算法类型选择推荐策略
        if algorithm == "mixed":
            recommendations = self._get_enhanced_mixed_recommendations(
                user_id, learned_word_ids, limit, weights, user_records
            )
        elif algorithm == "collaborative":
            recommendations = self._get_collaborative_recommendations(
                user_id, learned_word_ids, limit
            )
        elif algorithm == "deep_learning":
            recommendations = self._get_deep_learning_recommendations(
                user_id, learned_word_ids, limit
            )
        elif algorithm == "difficulty":
            recommendations = self._get_difficulty_based_recommendations(
                user_id, learned_word_ids, limit
            )
        elif algorithm == "frequency":
            recommendations = self._get_frequency_based_recommendations(
                user_id, learned_word_ids, limit
            )
        elif algorithm == "history":
            recommendations = self._get_history_based_recommendations(
                user_id, learned_word_ids, limit
            )
        elif algorithm == "random":
            recommendations = self._get_random_recommendations(user_id, learned_word_ids, limit)
        else:
            recommendations = self._get_enhanced_mixed_recommendations(
                user_id, learned_word_ids, limit, weights, user_records
            )

        # 应用多样性控制
        if self.diversity_controller and RECOMMENDATION_CONFIG["diversity"]["enabled"]:
            recommendations = self.diversity_controller.apply_mmr(
                recommendations, limit, user_records
            )
            recommendations = self.diversity_controller.limit_same_pos_ratio(recommendations)

        # 应用实时个性化调整
        if (
            self.realtime_personalizer
            and RECOMMENDATION_CONFIG["realtime_personalization"]["enabled"]
        ):
            for rec in recommendations:
                rec["recommendation_score"] = (
                    self.realtime_personalizer.adjust_recommendation_score(rec, user_id)
                )

        # 保存推荐记录
        self._save_recommendations(user_id, recommendations[:limit])

        # 缓存结果
        result = recommendations[:limit]
        recommendation_cache.set(cache_key, result)

        return result

    def _get_dynamic_weights(self, user_id: int, record_count: int) -> Dict[str, float]:
        """
        获取动态调整后的权重

        Args:
            user_id: 用户ID
            record_count: 学习记录数量

        Returns:
            权重字典
        """
        if self.weight_adjuster:
            return self.weight_adjuster.get_weights(user_id, record_count)
        return self.base_weights.copy()

    def _get_enhanced_mixed_recommendations(
        self,
        user_id: int,
        learned_word_ids: set,
        limit: int,
        weights: Dict[str, float],
        user_records: list,
    ) -> list:
        """
        增强版混合推荐算法

        Args:
            user_id: 用户ID
            learned_word_ids: 已学单词ID集合
            limit: 推荐数量
            weights: 算法权重
            user_records: 用户学习记录

        Returns:
            推荐单词列表
        """
        # 判断是否探索
        should_explore = False
        if self.weight_adjuster:
            should_explore = self.weight_adjuster.should_explore(user_id)

        # 获取各种推荐结果
        difficulty_recs = self._get_difficulty_based_recommendations(
            user_id, learned_word_ids, limit * 2
        )
        frequency_recs = self._get_frequency_based_recommendations(
            user_id, learned_word_ids, limit * 2
        )
        history_recs = self._get_history_based_recommendations(user_id, learned_word_ids, limit * 2)
        deep_learning_recs = self._get_deep_learning_recommendations(
            user_id, learned_word_ids, limit * 2
        )
        collaborative_recs = self._get_collaborative_recommendations(
            user_id, learned_word_ids, limit * 2
        )

        # 随机探索（如果需要）
        random_recs = []
        if should_explore:
            random_recs = self._get_random_recommendations(user_id, learned_word_ids, limit)
            # 探索时增加随机权重
            weights = weights.copy()
            weights["random_exploration"] = min(0.3, weights.get("random_exploration", 0.1) * 2)

        # 计算综合推荐分数
        all_candidates = {}

        # 难度推荐
        for word in difficulty_recs:
            word_id = word["id"]
            if word_id not in all_candidates:
                all_candidates[word_id] = {"word": word, "score": 0, "sources": []}
            score = word.get("recommendation_score", 0.5)
            all_candidates[word_id]["score"] += weights.get("difficulty_based", 0.25) * score
            all_candidates[word_id]["sources"].append("difficulty")

        # 词频推荐
        for word in frequency_recs:
            word_id = word["id"]
            if word_id not in all_candidates:
                all_candidates[word_id] = {"word": word, "score": 0, "sources": []}
            score = word.get("recommendation_score", 0.5)
            all_candidates[word_id]["score"] += weights.get("frequency_based", 0.20) * score
            all_candidates[word_id]["sources"].append("frequency")

        # 历史推荐
        for word in history_recs:
            word_id = word["id"]
            if word_id not in all_candidates:
                all_candidates[word_id] = {"word": word, "score": 0, "sources": []}
            score = word.get("recommendation_score", 0.5)
            all_candidates[word_id]["score"] += weights.get("learning_history", 0.20) * score
            all_candidates[word_id]["sources"].append("history")

        # 深度学习推荐
        for word in deep_learning_recs:
            word_id = word["id"]
            if word_id not in all_candidates:
                all_candidates[word_id] = {"word": word, "score": 0, "sources": []}
            score = word.get("recommendation_score", 0.5)
            all_candidates[word_id]["score"] += weights.get("deep_learning", 0.25) * score
            all_candidates[word_id]["sources"].append("deep_learning")

        # 协同过滤推荐
        for word in collaborative_recs:
            word_id = word["id"]
            if word_id not in all_candidates:
                all_candidates[word_id] = {"word": word, "score": 0, "sources": []}
            score = word.get("recommendation_score", 0.5)
            all_candidates[word_id]["score"] += weights.get("collaborative", 0.15) * score
            all_candidates[word_id]["sources"].append("collaborative")

        # 随机探索
        for word in random_recs:
            word_id = word["id"]
            if word_id not in all_candidates:
                all_candidates[word_id] = {"word": word, "score": 0, "sources": []}
            score = word.get("recommendation_score", 0.5)
            all_candidates[word_id]["score"] += weights.get("random_exploration", 0.10) * score
            all_candidates[word_id]["sources"].append("random")

        # 按分数排序
        sorted_candidates = sorted(all_candidates.values(), key=lambda x: x["score"], reverse=True)

        # 构建最终推荐列表
        recommendations = []
        for candidate in sorted_candidates[: limit * 2]:
            word = candidate["word"].copy()
            word["recommendation_score"] = candidate["score"]
            word["algorithm_type"] = self._determine_primary_algorithm(candidate["sources"])
            word["reason"] = self._generate_enhanced_reason(word, candidate["sources"])
            recommendations.append(word)

        return recommendations

    def _get_collaborative_recommendations(self, user_id, learned_word_ids, limit):
        """
        协同过滤推荐

        Args:
            user_id: 用户ID
            learned_word_ids: 已学单词集合
            limit: 推荐数量

        Returns:
            推荐单词列表
        """
        if not self.collaborative_filter:
            return []

        try:
            # 先尝试基于用户的协同过滤
            user_cf_recs = self.collaborative_filter.get_collaborative_recommendations(
                user_id, learned_word_ids, limit // 2
            )

            # 再尝试基于物品的协同过滤
            item_cf_recs = self.collaborative_filter.get_item_based_recommendations(
                user_id, learned_word_ids, limit // 2
            )

            # 合并去重
            all_recs = {}
            for rec in user_cf_recs + item_cf_recs:
                if rec["id"] not in all_recs:
                    all_recs[rec["id"]] = rec

            recommendations = list(all_recs.values())[:limit]

            # 添加推荐理由
            for rec in recommendations:
                rec["algorithm_type"] = "collaborative"
                rec["reason"] = "相似用户推荐：与您学习偏好相似的用户也学习了这个词"

            return recommendations

        except Exception as e:
            logger.warning("协同过滤推荐失败: %s", e)
            return []

    def _determine_primary_algorithm(self, sources: list) -> str:
        """
        确定主要算法类型

        Args:
            sources: 推荐来源列表

        Returns:
            主要算法类型
        """
        if not sources:
            return "mixed"

        # 优先级排序
        priority = [
            "deep_learning",
            "collaborative",
            "history",
            "frequency",
            "difficulty",
            "random",
        ]

        source_count = {}
        for source in sources:
            source_count[source] = source_count.get(source, 0) + 1

        # 按优先级和出现次数确定
        for algo in priority:
            if algo in source_count:
                return algo

        return sources[0] if sources else "mixed"

    def _generate_enhanced_reason(self, word: dict, sources: list) -> str:
        """
        生成增强版推荐理由

        Args:
            word: 单词信息
            sources: 推荐来源列表

        Returns:
            推荐理由
        """
        difficulty = word.get("difficulty_level", 3)
        frequency = word.get("frequency_rank", 1000)
        tag = word.get("tag", "")

        # 多来源组合推荐
        if len(sources) > 2:
            if "deep_learning" in sources and "collaborative" in sources:
                return "AI+协同推荐：智能匹配您的学习偏好"
            elif "deep_learning" in sources:
                return "AI智能推荐：基于您的学习模式精选"
            elif "collaborative" in sources:
                return "相似用户推荐：学友都在学的高频词"

        # 单一来源推荐
        if "deep_learning" in sources:
            if frequency <= 100:
                return "AI推荐：高频核心词汇，智能匹配"
            elif "CET4" in tag or "四级" in tag:
                return "AI推荐：四级核心词汇"
            else:
                return "AI智能推荐：个性化学习精选"

        elif "collaborative" in sources:
            return "协同推荐：与您相似的学习者也在学"

        elif "frequency" in sources:
            if frequency <= 100:
                return "高频词汇：最常用的英语单词TOP100"
            elif frequency <= 500:
                return "常用词汇：日常必备单词"
            else:
                return "重要词汇：学习频率较高的词"

        elif "difficulty" in sources:
            if difficulty <= 2:
                return "基础词汇：适合当前学习阶段"
            elif difficulty <= 4:
                return "进阶词汇：稳步提升难度"
            else:
                return "高阶词汇：挑战学习极限"

        elif "history" in sources:
            return "智能推荐：基于您的学习历史"

        elif "random" in sources:
            return "探索发现：尝试新的学习领域"

        else:
            return "智能推荐：为您精选"

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
            if hasattr(self.deep_learning_recommender, "_try_load_model"):
                self.deep_learning_recommender._try_load_model(user_id)

            # 如果模型未训练，尝试为当前用户训练
            if not self.deep_learning_recommender.is_trained:
                logger.info("为用户 %s 训练深度学习模型...", user_id)
                success = self.deep_learning_recommender.train_model_for_user(user_id)
                if not success:
                    logger.warning("深度学习模型训练失败，使用传统推荐")
                    return self._get_difficulty_based_recommendations(
                        user_id, learned_word_ids, limit
                    )

            # 使用深度学习模型获取推荐
            recommendations = self.deep_learning_recommender.get_deep_learning_recommendations(
                user_id, limit
            )

            # 添加算法类型标识和推荐理由
            for rec in recommendations:
                rec["algorithm_type"] = "deep_learning"
                rec["reason"] = self._generate_recommendation_reason(rec, "deep_learning")

            return recommendations
        except Exception as e:
            logger.warning("深度学习推荐失败: %s", e)
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
            if algorithm_type == "deep_learning":
                # 基于深度学习模型的推荐理由
                mastery_level = recommendation.get("mastery_level", 0)
                difficulty = recommendation.get("difficulty_level", 3)
                frequency_rank = recommendation.get("frequency_rank", 1000)
                tag = recommendation.get("tag", "")

                # 根据考试标签选择理由
                if "四级" in tag or "六级" in tag:
                    return "AI推荐：四六级必备词汇"
                elif "考研" in tag:
                    return "AI推荐：考研核心词汇"
                elif "雅思" in tag or "托福" in tag:
                    return "AI推荐：留学考试词汇"
                elif "GRE" in tag:
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

            elif algorithm_type == "difficulty_based":
                # 基于难度的推荐理由
                difficulty = recommendation.get("difficulty_level", 3)
                frequency_rank = recommendation.get("frequency_rank", 1000)

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

            elif algorithm_type == "frequency_based":
                # 基于频率的推荐理由
                frequency_rank = recommendation.get("frequency_rank", 1000)
                if frequency_rank <= LEARNING_PARAMS["frequency_threshold"]:
                    return "高频词汇：使用频繁"
                elif frequency_rank <= 1000:
                    return "常用词汇：实用性强"
                else:
                    return "扩展词汇：丰富表达"

            elif algorithm_type == "collaborative":
                # 基于协同过滤的推荐理由
                return "相似用户：学习偏好匹配"

            elif algorithm_type == "random":
                # 随机探索的推荐理由
                difficulty = recommendation.get("difficulty_level", 3)
                if difficulty <= 2:
                    return "随机探索：发现新词汇"
                elif difficulty <= 4:
                    return "随机推荐：拓展词汇量"
                else:
                    return "随机挑战：突破舒适区"

            elif algorithm_type == "mixed":
                # 混合推荐：根据单词特征智能选择理由
                difficulty = recommendation.get("difficulty_level", 3)
                frequency_rank = recommendation.get("frequency_rank", 1000)
                domain = recommendation.get("domain", [])
                tag = recommendation.get("tag", "")

                # 根据考试标签选择理由
                if "四级" in tag or "六级" in tag:
                    return "考试词汇：四六级必备"
                elif "考研" in tag:
                    return "考研词汇：学术进阶"
                elif "雅思" in tag or "托福" in tag:
                    return "留学词汇：国际考试"
                elif "GRE" in tag:
                    return "GRE词汇：学术精英"

                # 根据使用领域选择理由
                elif "spoken" in domain:
                    return "口语词汇：日常交流"
                elif "academic" in domain:
                    return "学术词汇：专业表达"
                elif "business" in domain:
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
            logger.debug("生成推荐理由失败: %s", e)
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
            avg_mastery = sum(record["mastery_level"] for record in user_records) / len(
                user_records
            )
            target_difficulty = min(6, max(1, int(avg_mastery * 6) + 1))

        # 考虑实时个性化
        if self.realtime_personalizer:
            adjusted_difficulty = self.realtime_personalizer.get_session_adjusted_difficulty(
                user_id
            )
            if adjusted_difficulty != 3:  # 如果有会话数据
                target_difficulty = adjusted_difficulty

        # 获取指定难度的单词
        all_words = self.words_crud.list_all(limit=500)
        difficulty_words = [
            word
            for word in all_words
            if word["difficulty_level"] == target_difficulty and word["id"] not in learned_word_ids
        ]

        # 该难度下无可用词时，退化为「任意未学词」
        if not difficulty_words:
            difficulty_words = [word for word in all_words if word["id"] not in learned_word_ids]
        if not difficulty_words:
            return []

        # 随机选择
        k = min(limit, len(difficulty_words))
        selected_words = random.sample(difficulty_words, k)

        # 添加推荐分数
        for word in selected_words:
            word["recommendation_score"] = 0.8  # 难度匹配度高

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
            avg_mastery = sum(record["mastery_level"] for record in user_records) / len(
                user_records
            )
            base_difficulty = min(6, max(1, int(avg_mastery * 6) + 1))
            min_difficulty = max(1, base_difficulty - 1)
            max_difficulty = min(6, base_difficulty + 1)

        # 获取指定难度范围内的高频单词
        all_words = self.words_crud.list_all(limit=500)
        frequency_words = [
            word
            for word in all_words
            if word["id"] not in learned_word_ids
            and min_difficulty <= word["difficulty_level"] <= max_difficulty
        ]

        # 按词频排序（frequency_rank越小越高频）
        frequency_words.sort(key=lambda x: x["frequency_rank"])

        # 选择前limit个
        selected_words = frequency_words[:limit]

        # 添加推荐分数
        for i, word in enumerate(selected_words):
            # 词频越高，分数越高
            word["recommendation_score"] = max(0.1, 1.0 - (i / len(selected_words)) * 0.5)

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
        candidate_words = [word for word in all_words if word["id"] not in learned_word_ids]

        # 计算相似度分数
        for word in candidate_words:
            similarity_score = self._calculate_word_similarity(word, user_preferences)
            word["recommendation_score"] = similarity_score

        # 按相似度排序
        candidate_words.sort(key=lambda x: x["recommendation_score"], reverse=True)

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
            avg_mastery = sum(record["mastery_level"] for record in user_records) / len(
                user_records
            )
            base_difficulty = min(6, max(1, int(avg_mastery * 6) + 1))
            min_difficulty = max(1, base_difficulty - 1)
            max_difficulty = min(6, base_difficulty + 1)

        # 获取指定难度范围内的未学单词
        all_words = self.words_crud.list_all(limit=500)
        unlearned_words = [
            word
            for word in all_words
            if word["id"] not in learned_word_ids
            and min_difficulty <= word["difficulty_level"] <= max_difficulty
        ]

        # 难度范围内无词时退化为任意未学词
        if not unlearned_words:
            unlearned_words = [word for word in all_words if word["id"] not in learned_word_ids]
        if not unlearned_words:
            return []

        k = min(limit, len(unlearned_words))
        selected_words = random.sample(unlearned_words, k)

        # 添加推荐分数
        for word in selected_words:
            word["recommendation_score"] = random.uniform(0.1, 0.5)  # 随机分数

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
            "preferred_difficulty": [],
            "preferred_pos": [],
            "preferred_tags": [],
            "learning_speed": 0.0,
        }

        if not user_records:
            return preferences

        # 分析难度偏好
        difficulty_counts = {}
        for record in user_records:
            # 这里需要根据word_id获取单词信息
            # 简化处理，假设有difficulty_level字段
            difficulty = record.get("difficulty_level", 3)
            difficulty_counts[difficulty] = difficulty_counts.get(difficulty, 0) + 1

        preferences["preferred_difficulty"] = (
            max(difficulty_counts.keys(), key=difficulty_counts.get) if difficulty_counts else 3
        )

        # 分析学习速度
        total_reviews = sum(record["review_count"] for record in user_records)
        preferences["learning_speed"] = total_reviews / len(user_records) if user_records else 1.0

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
        if word["difficulty_level"] == user_preferences["preferred_difficulty"]:
            score += 0.4

        # 词频权重
        if word["frequency_rank"] < 1000:  # 高频词
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
                word_id=word["id"],
                recommendation_score=word.get("recommendation_score", 0.5),
                recommendation_type=word.get("algorithm_type", "mixed"),
                reason=word.get("reason", ""),
                created_at=datetime.now(),
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
            return max(0.1, 1.0 - word["frequency_rank"] / 10000)

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

    def record_feedback(
        self,
        user_id: int,
        word_id: int,
        algorithm_type: str,
        mastery_before: float,
        mastery_after: float,
        is_correct: bool,
    ):
        """
        记录用户反馈（用于权重调整）

        Args:
            user_id: 用户ID
            word_id: 单词ID
            algorithm_type: 推荐算法类型
            mastery_before: 学习前掌握度
            mastery_after: 学习后掌握度
            is_correct: 是否答对
        """
        if self.weight_adjuster:
            self.weight_adjuster.record_algorithm_feedback(
                user_id, algorithm_type, mastery_before, mastery_after, is_correct
            )

        if self.realtime_personalizer:
            # 获取单词难度
            word = self.words_crud.read(word_id)
            difficulty = word.get("difficulty_level", 3) if word else 3

            # 估算响应时间（简化）
            response_time = 10 if is_correct else 20

            self.realtime_personalizer.update_session(
                user_id, word_id, is_correct, response_time, difficulty
            )

    def end_learning_session(self, user_id: int) -> dict:
        """
        结束学习会话

        Args:
            user_id: 用户ID

        Returns:
            会话摘要
        """
        if self.realtime_personalizer:
            summary = self.realtime_personalizer.end_session_and_learn(user_id)
            return summary
        return {}

    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass
