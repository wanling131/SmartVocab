"""推荐算法增强模块。

包含：协同过滤、动态权重调整、多样性控制、冷启动策略、探索利用平衡。

Author: SmartVocab Team
"""

import logging
import math
import random
from collections import defaultdict
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

from config import RECOMMENDATION_CONFIG
from tools.learning_records_crud import LearningRecordsCRUD
from tools.words_crud import WordsCRUD

logger = logging.getLogger(__name__)


class CollaborativeFiltering:
    """
    协同过滤推荐模块
    支持用户协同过滤和物品协同过滤
    """

    def __init__(self) -> None:
        """初始化协同过滤模块。"""
        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()
        self.config = RECOMMENDATION_CONFIG["collaborative_filtering"]

        # 缓存
        self._user_item_matrix: Optional[Dict[int, Dict[int, float]]] = None
        self._user_similarity_cache: Dict[Tuple[int, int], float] = {}
        self._item_similarity_cache: Dict[Tuple[int, int], float] = {}

    def build_user_item_matrix(self) -> Dict[int, Dict[int, float]]:
        """构建用户-物品矩阵。

        Returns:
            Dict[int, Dict[int, float]]: 用户-物品矩阵，格式为 {user_id: {word_id: mastery_level}}。
        """
        logger.info("构建用户-物品矩阵...")
        matrix = defaultdict(dict)

        # 获取所有学习记录
        records = self.learning_records_crud.list_all(limit=50000)

        for record in records:
            user_id = record["user_id"]
            word_id = record["word_id"]
            mastery = record.get("mastery_level", 0.5)

            # 使用掌握程度作为隐式评分
            # 考虑复习次数加成
            review_count = record.get("review_count", 0)
            adjusted_rating = min(1.0, mastery + review_count * 0.02)

            matrix[user_id][word_id] = adjusted_rating

        self._user_item_matrix = dict(matrix)
        logger.info("用户-物品矩阵构建完成: %d 用户", len(self._user_item_matrix))
        return self._user_item_matrix

    def calculate_user_similarity(self, user1_id: int, user2_id: int) -> float:
        """计算两个用户之间的余弦相似度。

        Args:
            user1_id: 用户1的ID。
            user2_id: 用户2的ID。

        Returns:
            float: 相似度，范围 [0, 1]。
        """
        cache_key = (min(user1_id, user2_id), max(user1_id, user2_id))
        if cache_key in self._user_similarity_cache:
            return self._user_similarity_cache[cache_key]

        if self._user_item_matrix is None:
            self.build_user_item_matrix()

        user1_items = self._user_item_matrix.get(user1_id, {})
        user2_items = self._user_item_matrix.get(user2_id, {})

        # 找到共同学习的单词
        common_items = set(user1_items.keys()) & set(user2_items.keys())

        min_common = self.config["min_common_items"]
        if len(common_items) < min_common:
            return 0.0

        # 计算余弦相似度
        dot_product = sum(user1_items[item] * user2_items[item] for item in common_items)
        norm1 = math.sqrt(sum(v**2 for v in user1_items.values()))
        norm2 = math.sqrt(sum(v**2 for v in user2_items.values()))

        if norm1 == 0 or norm2 == 0:
            return 0.0

        similarity = dot_product / (norm1 * norm2)
        self._user_similarity_cache[cache_key] = similarity

        return similarity

    def find_similar_users(self, user_id: int, k: Optional[int] = None) -> List[Tuple[int, float]]:
        """找到与目标用户最相似的k个用户。

        Args:
            user_id: 目标用户ID。
            k: 返回数量，默认使用配置值。

        Returns:
            List[Tuple[int, float]]: 相似用户列表，格式为 [(user_id, similarity), ...]。
        """
        if k is None:
            k = self.config["neighbor_count"]

        if self._user_item_matrix is None:
            self.build_user_item_matrix()

        similarities = []
        threshold = self.config["similarity_threshold"]

        for other_user_id in self._user_item_matrix.keys():
            if other_user_id == user_id:
                continue

            sim = self.calculate_user_similarity(user_id, other_user_id)
            if sim >= threshold:
                similarities.append((other_user_id, sim))

        # 按相似度排序，返回top-k
        similarities.sort(key=lambda x: x[1], reverse=True)
        return similarities[:k]

    def get_collaborative_recommendations(
        self, user_id: int, learned_word_ids: Set[int], limit: int = 20
    ) -> List[Dict[str, any]]:
        """基于用户的协同过滤推荐。

        Args:
            user_id: 目标用户ID。
            learned_word_ids: 已学单词ID集合。
            limit: 返回数量。

        Returns:
            List[Dict[str, any]]: 推荐单词列表。
        """
        if not self.config["enabled"]:
            return []

        try:
            if self._user_item_matrix is None:
                self.build_user_item_matrix()

            # 找到相似用户
            similar_users = self.find_similar_users(user_id)

            if not similar_users:
                logger.debug("用户 %d 无相似用户，跳过协同过滤", user_id)
                return []

            # 收集相似用户学习过但目标用户未学习的单词
            candidate_scores = defaultdict(float)
            total_weight = 0

            for neighbor_id, similarity in similar_users:
                neighbor_items = self._user_item_matrix.get(neighbor_id, {})
                total_weight += similarity

                for word_id, rating in neighbor_items.items():
                    if word_id not in learned_word_ids:
                        # 加权评分
                        candidate_scores[word_id] += similarity * rating

            if total_weight == 0:
                return []

            # 归一化分数
            for word_id in candidate_scores:
                candidate_scores[word_id] /= total_weight

            # 获取单词详情
            all_words = self.words_crud.list_all(limit=5000)
            word_dict = {w["id"]: w for w in all_words}

            # 构建推荐列表
            recommendations = []
            for word_id, score in sorted(
                candidate_scores.items(), key=lambda x: x[1], reverse=True
            )[: limit * 2]:
                if word_id in word_dict:
                    word = word_dict[word_id].copy()
                    word["recommendation_score"] = min(1.0, score)
                    word["algorithm_type"] = "collaborative_user"
                    recommendations.append(word)

            return recommendations[:limit]

        except Exception as e:
            logger.warning("协同过滤推荐失败: %s", e)
            return []

    def calculate_item_similarity(self, word1_id: int, word2_id: int) -> float:
        """计算两个单词之间的共现相似度（基于物品的协同过滤）。

        Args:
            word1_id: 单词1的ID。
            word2_id: 单词2的ID。

        Returns:
            float: 相似度，范围 [0, 1]。
        """
        cache_key = (min(word1_id, word2_id), max(word1_id, word2_id))
        if cache_key in self._item_similarity_cache:
            return self._item_similarity_cache[cache_key]

        if self._user_item_matrix is None:
            self.build_user_item_matrix()

        # 找到同时学习这两个单词的用户
        users_with_word1 = set()
        users_with_word2 = set()

        for user_id, items in self._user_item_matrix.items():
            if word1_id in items:
                users_with_word1.add(user_id)
            if word2_id in items:
                users_with_word2.add(user_id)

        # Jaccard相似度
        intersection = len(users_with_word1 & users_with_word2)
        union = len(users_with_word1 | users_with_word2)

        if union == 0:
            return 0.0

        similarity = intersection / union
        self._item_similarity_cache[cache_key] = similarity
        return similarity

    def get_item_based_recommendations(
        self, user_id: int, learned_word_ids: Set[int], limit: int = 20
    ) -> List[Dict[str, any]]:
        """基于物品的协同过滤推荐。

        Args:
            user_id: 用户ID。
            learned_word_ids: 已学单词集合。
            limit: 返回数量。

        Returns:
            List[Dict[str, any]]: 推荐单词列表。
        """
        if not self.config.get("item_based_enabled", True):
            return []

        try:
            if self._user_item_matrix is None:
                self.build_user_item_matrix()

            user_items = self._user_item_matrix.get(user_id, {})
            if not user_items:
                return []

            # 获取所有单词
            all_words = self.words_crud.list_all(limit=5000)
            all_word_ids = {w["id"] for w in all_words}
            word_dict = {w["id"]: w for w in all_words}

            # 计算未学单词与已学单词的相似度
            candidate_scores = defaultdict(float)

            # 只考虑用户高掌握度的单词
            well_learned = {wid for wid, mastery in user_items.items() if mastery >= 0.5}

            for learned_id in well_learned:
                for candidate_id in all_word_ids - learned_word_ids:
                    sim = self.calculate_item_similarity(learned_id, candidate_id)
                    if sim > 0:
                        # 加权：考虑用户对该词的掌握程度
                        candidate_scores[candidate_id] += sim * user_items[learned_id]

            # 归一化并构建推荐
            recommendations = []
            max_score = max(candidate_scores.values()) if candidate_scores else 1

            for word_id, score in sorted(
                candidate_scores.items(), key=lambda x: x[1], reverse=True
            )[: limit * 2]:
                if word_id in word_dict:
                    word = word_dict[word_id].copy()
                    word["recommendation_score"] = min(1.0, score / max_score)
                    word["algorithm_type"] = "collaborative_item"
                    recommendations.append(word)

            return recommendations[:limit]

        except Exception as e:
            logger.warning("基于物品的协同过滤失败: %s", e)
            return []


class DynamicWeightAdjuster:
    """动态权重调整器。

    根据用户行为和反馈动态调整各算法权重。
    """

    def __init__(self) -> None:
        """初始化动态权重调整器。"""
        self.config = RECOMMENDATION_CONFIG["dynamic_weights"]
        self.exploration_config = RECOMMENDATION_CONFIG["exploration_exploitation"]

        # 基础权重
        self.base_weights: Dict[str, float] = {
            "difficulty_based": 0.25,
            "frequency_based": 0.20,
            "learning_history": 0.20,
            "deep_learning": 0.25,
            "random_exploration": 0.10,
        }

        # 用户个性化权重缓存
        self._user_weights: Dict[int, Dict[str, float]] = {}

        # 算法效果追踪
        self._algorithm_performance: Dict[str, Dict[str, any]] = defaultdict(
            lambda: {"attempts": 0, "successes": 0, "total_mastery_gain": 0.0}
        )

        # 用户学习轮次（用于探索衰减）
        self._user_episodes: Dict[int, int] = defaultdict(int)

    def get_weights(self, user_id: int, record_count: int = 0) -> Dict[str, float]:
        """获取用户的个性化权重。

        Args:
            user_id: 用户ID。
            record_count: 用户学习记录数量。

        Returns:
            Dict[str, float]: 算法权重字典。
        """
        # 数据不足时使用基础权重
        min_records = self.config["min_records_for_personalization"]
        if record_count < min_records:
            return self.base_weights.copy()

        # 检查缓存
        if user_id in self._user_weights:
            return self._user_weights[user_id].copy()

        # 根据算法表现调整权重
        personalized = self._calculate_personalized_weights(user_id)
        self._user_weights[user_id] = personalized

        return personalized

    def _calculate_personalized_weights(self, user_id: int) -> Dict[str, float]:
        """计算用户的个性化权重。

        Args:
            user_id: 用户ID。

        Returns:
            Dict[str, float]: 个性化权重字典。
        """
        weights = self.base_weights.copy()

        # 收集各算法的表现
        performance_scores = {}
        for algo in weights.keys():
            perf = self._algorithm_performance.get(
                f"{user_id}_{algo}", {"attempts": 0, "successes": 0, "total_mastery_gain": 0.0}
            )

            if perf["attempts"] > 0:
                # 成功率 + 平均掌握度提升
                success_rate = perf["successes"] / perf["attempts"]
                avg_gain = perf["total_mastery_gain"] / perf["attempts"]
                performance_scores[algo] = success_rate * 0.6 + avg_gain * 0.4
            else:
                performance_scores[algo] = 0.5  # 默认中等表现

        # 归一化表现分数
        total_perf = sum(performance_scores.values())
        if total_perf > 0:
            normalized_perf = {k: v / total_perf for k, v in performance_scores.items()}
        else:
            normalized_perf = {k: 1 / len(weights) for k in weights}

        # 混合基础权重和表现权重
        adaptation_rate = self.config["weight_adaptation_rate"]
        for algo in weights:
            weights[algo] = (1 - adaptation_rate) * weights[
                algo
            ] + adaptation_rate * normalized_perf[algo] * len(weights)

        # 归一化
        total = sum(weights.values())
        weights = {k: v / total for k, v in weights.items()}

        return weights

    def record_algorithm_feedback(
        self,
        user_id: int,
        algorithm_type: str,
        mastery_before: float,
        mastery_after: float,
        is_correct: bool,
    ) -> None:
        """记录算法反馈，用于权重调整。

        Args:
            user_id: 用户ID。
            algorithm_type: 算法类型。
            mastery_before: 学习前掌握度。
            mastery_after: 学习后掌握度。
            is_correct: 是否答对。
        """
        key = f"{user_id}_{algorithm_type}"
        perf = self._algorithm_performance[key]

        perf["attempts"] += 1
        if is_correct:
            perf["successes"] += 1

        mastery_gain = max(0, mastery_after - mastery_before)
        perf["total_mastery_gain"] += mastery_gain

        # 清除权重缓存，强制重新计算
        if user_id in self._user_weights:
            del self._user_weights[user_id]

    def get_exploration_rate(self, user_id: int) -> float:
        """获取用户的探索率（epsilon-greedy策略）。

        Args:
            user_id: 用户ID。

        Returns:
            float: 探索率，范围 [0, 1]。
        """
        episode = self._user_episodes[user_id]
        self._user_episodes[user_id] += 1

        epsilon_start = self.exploration_config["epsilon_start"]
        epsilon_end = self.exploration_config["epsilon_end"]
        decay_episodes = self.exploration_config["epsilon_decay_episodes"]

        # 指数衰减
        epsilon = epsilon_end + (epsilon_start - epsilon_end) * math.exp(-episode / decay_episodes)

        return epsilon

    def should_explore(self, user_id: int) -> bool:
        """判断当前是否应该探索。

        Args:
            user_id: 用户ID。

        Returns:
            bool: 是否进行探索。
        """
        epsilon = self.get_exploration_rate(user_id)
        return random.random() < epsilon

    def select_algorithm_ucb(self, user_id: int, algorithms: List[str]) -> str:
        """使用UCB算法选择推荐算法。

        Args:
            user_id: 用户ID。
            algorithms: 可用算法列表。

        Returns:
            str: 选择的算法名称。
        """
        alpha = self.exploration_config["ucb_alpha"]
        total_attempts = (
            sum(self._algorithm_performance[f"{user_id}_{algo}"]["attempts"] for algo in algorithms)
            + 1
        )  # 避免除零

        best_algo = None
        best_ucb = -float("inf")

        for algo in algorithms:
            key = f"{user_id}_{algo}"
            perf = self._algorithm_performance[key]

            if perf["attempts"] == 0:
                # 未尝试过的算法优先探索
                return algo

            # 平均奖励
            avg_reward = perf["total_mastery_gain"] / perf["attempts"]

            # UCB置信度上界
            confidence = alpha * math.sqrt(math.log(total_attempts) / perf["attempts"])

            ucb_value = avg_reward + confidence

            if ucb_value > best_ucb:
                best_ucb = ucb_value
                best_algo = algo

        return best_algo or random.choice(algorithms)


class DiversityController:
    """多样性控制器。

    使用MMR算法确保推荐结果的多样性。
    """

    def __init__(self) -> None:
        """初始化多样性控制器。"""
        self.config = RECOMMENDATION_CONFIG["diversity"]

    def apply_mmr(
        self,
        candidates: List[Dict[str, any]],
        limit: int,
        user_history: Optional[List[Dict[str, any]]] = None,
    ) -> List[Dict[str, any]]:
        """应用MMR（Maximal Marginal Relevance）算法选择多样化推荐。

        Args:
            candidates: 候选单词列表。
            limit: 返回数量。
            user_history: 用户历史学习记录（可选）。

        Returns:
            List[Dict[str, any]]: 多样化后的推荐列表。
        """
        if not self.config["enabled"] or len(candidates) <= limit:
            return candidates[:limit]

        lambda_param = self.config["mmr_lambda"]
        selected = []
        remaining = candidates.copy()

        # 构建用户历史特征（用于避免推荐过于相似的词）
        history_features = self._extract_history_features(user_history or [])

        while len(selected) < limit and remaining:
            best_score = -float("inf")
            best_idx = 0

            for i, candidate in enumerate(remaining):
                # 相关性分数
                relevance = candidate.get("recommendation_score", 0.5)

                # 多样性惩罚（与已选词的相似度）
                diversity_penalty = 0
                if selected:
                    diversity_penalty = max(
                        self._calculate_similarity(candidate, s) for s in selected
                    )

                # 历史相似度惩罚（避免推荐与已学词过于相似的新词）
                history_penalty = 0
                if history_features:
                    history_penalty = (
                        self._calculate_history_similarity(candidate, history_features) * 0.3
                    )

                # MMR分数
                mmr_score = (
                    lambda_param * relevance
                    - (1 - lambda_param) * diversity_penalty
                    - history_penalty
                )

                if mmr_score > best_score:
                    best_score = mmr_score
                    best_idx = i

            selected.append(remaining.pop(best_idx))

        return selected

    def _calculate_similarity(self, word1: Dict[str, any], word2: Dict[str, any]) -> float:
        """计算两个单词之间的相似度。

        Args:
            word1: 单词1信息。
            word2: 单词2信息。

        Returns:
            float: 相似度，范围 [0, 1]。
        """
        similarity = 0.0

        # 难度相似度
        diff1 = word1.get("difficulty_level", 3)
        diff2 = word2.get("difficulty_level", 3)
        similarity += 1 - abs(diff1 - diff2) / 5

        # 词性相似度
        pos1 = word1.get("pos", "")
        pos2 = word2.get("pos", "")
        if pos1 and pos2:
            similarity += 0.3 if pos1 == pos2 else 0

        # 词频相似度
        freq1 = word1.get("frequency_rank", 1000)
        freq2 = word2.get("frequency_rank", 1000)
        freq_sim = 1 - min(1, abs(freq1 - freq2) / 5000)
        similarity += freq_sim * 0.3

        # 标签相似度
        tag1 = set(word1.get("tag", "").split(",")) if word1.get("tag") else set()
        tag2 = set(word2.get("tag", "").split(",")) if word2.get("tag") else set()
        if tag1 and tag2:
            jaccard = len(tag1 & tag2) / len(tag1 | tag2)
            similarity += jaccard * 0.4

        return min(1.0, similarity / 2.0)

    def _extract_history_features(self, history: List[Dict[str, any]]) -> Dict[str, any]:
        """提取用户历史学习特征。

        Args:
            history: 用户历史学习记录列表。

        Returns:
            Dict[str, any]: 历史特征字典。
        """
        if not history:
            return {}

        features = {
            "avg_difficulty": 0,
            "common_pos": {},
            "common_tags": set(),
            "frequency_range": [float("inf"), 0],
        }

        difficulties = []
        pos_counts = defaultdict(int)
        all_tags = set()

        for record in history:
            # 这里假设record包含word信息，实际可能需要关联查询
            if "difficulty_level" in record:
                difficulties.append(record["difficulty_level"])

            if "pos" in record:
                pos_counts[record["pos"]] += 1

            if "tag" in record and record["tag"]:
                all_tags.update(record["tag"].split(","))

        if difficulties:
            features["avg_difficulty"] = sum(difficulties) / len(difficulties)

        features["common_pos"] = dict(pos_counts)
        features["common_tags"] = all_tags

        return features

    def _calculate_history_similarity(
        self, candidate: Dict[str, any], history_features: Dict[str, any]
    ) -> float:
        """计算候选词与用户历史的相似度。

        Args:
            candidate: 候选单词信息。
            history_features: 用户历史特征。

        Returns:
            float: 相似度，范围 [0, 1]。
        """
        if not history_features:
            return 0.0

        similarity = 0.0

        # 难度相似
        if history_features.get("avg_difficulty"):
            diff_diff = abs(
                candidate.get("difficulty_level", 3) - history_features["avg_difficulty"]
            )
            similarity += max(0, 1 - diff_diff / 3) * 0.4

        # 词性相似
        candidate_pos = candidate.get("pos", "")
        if candidate_pos and candidate_pos in history_features.get("common_pos", {}):
            pos_freq = history_features["common_pos"][candidate_pos]
            similarity += min(0.3, pos_freq * 0.05)

        return similarity

    def ensure_difficulty_spread(
        self, recommendations: List[Dict[str, any]]
    ) -> List[Dict[str, any]]:
        """确保推荐结果的难度分布合理。

        Args:
            recommendations: 推荐列表。

        Returns:
            List[Dict[str, any]]: 调整后的推荐列表。
        """
        if not self.config["enabled"]:
            return recommendations

        result = []

        # 按难度分组
        by_difficulty = defaultdict(list)
        for rec in recommendations:
            diff = rec.get("difficulty_level", 3)
            by_difficulty[diff].append(rec)

        # 轮询各难度级别，确保多样性
        max_len = max(len(v) for v in by_difficulty.values()) if by_difficulty else 0
        difficulty_levels = sorted(by_difficulty.keys())

        for i in range(max_len):
            for diff in difficulty_levels:
                if i < len(by_difficulty[diff]):
                    result.append(by_difficulty[diff][i])

        return result

    def limit_same_pos_ratio(self, recommendations: List[Dict[str, any]]) -> List[Dict[str, any]]:
        """限制同一词性的比例。

        Args:
            recommendations: 推荐列表。

        Returns:
            List[Dict[str, any]]: 调整后的推荐列表。
        """
        if not self.config["enabled"]:
            return recommendations

        max_ratio = self.config["max_same_pos_ratio"]
        pos_counts = defaultdict(int)
        result = []

        for rec in recommendations:
            pos = rec.get("pos", "other")
            current_ratio = pos_counts[pos] / (len(result) + 1) if result else 0

            if current_ratio < max_ratio or len(result) < 3:
                result.append(rec)
                pos_counts[pos] += 1

        return result


class ColdStartHandler:
    """冷启动处理器。

    为新用户提供智能的初始推荐策略。
    """

    def __init__(self) -> None:
        """初始化冷启动处理器。"""
        self.config = RECOMMENDATION_CONFIG["cold_start"]
        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()

        # 热门词缓存
        self._popular_words: Optional[List[Dict[str, any]]] = None

    def get_cold_start_recommendations(self, user_id: int, limit: int = 20) -> List[Dict[str, any]]:
        """为新用户生成冷启动推荐。

        Args:
            user_id: 用户ID。
            limit: 返回数量。

        Returns:
            List[Dict[str, any]]: 推荐单词列表。
        """
        recommendations = []

        # 策略1：热门词推荐
        if self.config["use_popularity"]:
            popular = self._get_popular_words(limit // 2)
            recommendations.extend(popular)

        # 策略2：基础难度词
        diff_range = self.config["default_difficulty_range"]
        basic_words = self._get_basic_words(diff_range, limit // 2)
        recommendations.extend(basic_words)

        # 去重
        seen = set()
        unique_recommendations = []
        for rec in recommendations:
            if rec["id"] not in seen:
                seen.add(rec["id"])
                unique_recommendations.append(rec)

        # 为每个推荐添加理由
        for rec in unique_recommendations:
            rec["algorithm_type"] = "cold_start"
            rec["reason"] = self._generate_cold_start_reason(rec)

        return unique_recommendations[:limit]

    def _get_popular_words(self, limit: int) -> List[Dict[str, any]]:
        """获取热门单词（被最多用户学习过的词）。

        Args:
            limit: 返回数量。

        Returns:
            List[Dict[str, any]]: 热门单词列表。
        """
        if self._popular_words is not None:
            return self._popular_words[:limit]

        try:
            # 统计每个单词被多少用户学习过
            records = self.learning_records_crud.list_all(limit=50000)

            word_user_count = defaultdict(int)
            word_mastery_sum = defaultdict(float)

            for record in records:
                word_id = record["word_id"]
                word_user_count[word_id] += 1
                word_mastery_sum[word_id] += record.get("mastery_level", 0)

            # 计算热度分数：用户数 * 平均掌握度
            word_scores = {}
            for word_id, count in word_user_count.items():
                avg_mastery = word_mastery_sum[word_id] / count
                # 热度 = 流行度 * 掌握度（优先推荐大家都能掌握的词）
                word_scores[word_id] = count * (0.5 + avg_mastery * 0.5)

            # 获取单词详情
            all_words = self.words_crud.list_all(limit=5000)
            word_dict = {w["id"]: w for w in all_words}

            # 排序并构建推荐
            popular = []
            for word_id, score in sorted(word_scores.items(), key=lambda x: x[1], reverse=True)[
                : limit * 2
            ]:
                if word_id in word_dict:
                    word = word_dict[word_id].copy()
                    word["recommendation_score"] = min(1.0, score / 100)
                    word["popularity_rank"] = len(popular) + 1
                    popular.append(word)

            self._popular_words = popular
            return popular[:limit]

        except Exception as e:
            logger.warning("获取热门词失败: %s", e)
            return []

    def _get_basic_words(self, difficulty_range: List[int], limit: int) -> List[Dict[str, any]]:
        """获取基础难度的单词。

        Args:
            difficulty_range: 难度范围 [min, max]。
            limit: 返回数量。

        Returns:
            List[Dict[str, any]]: 基础单词列表。
        """
        try:
            min_diff, max_diff = difficulty_range

            all_words = self.words_crud.list_all(limit=500)
            basic_words = [
                w for w in all_words if min_diff <= w.get("difficulty_level", 3) <= max_diff
            ]

            # 按词频排序（高频优先）
            basic_words.sort(key=lambda x: x.get("frequency_rank", 1000))

            recommendations = []
            for word in basic_words[:limit]:
                rec = word.copy()
                freq = rec.get("frequency_rank", 1000)
                rec["recommendation_score"] = max(0.3, 1 - freq / 5000)
                recommendations.append(rec)

            return recommendations

        except Exception as e:
            logger.warning("获取基础词失败: %s", e)
            return []

    def _generate_cold_start_reason(self, word: Dict[str, any]) -> str:
        """生成冷启动推荐理由。

        Args:
            word: 单词信息。

        Returns:
            str: 推荐理由字符串。
        """
        difficulty = word.get("difficulty_level", 3)
        frequency = word.get("frequency_rank", 1000)
        tag = word.get("tag", "")

        if frequency <= 100:
            return "高频词汇：最常用的英语单词"
        elif frequency <= 500:
            return "核心词汇：日常必备单词"
        elif "CET4" in tag or "四级" in tag:
            return "四级词汇：大学基础单词"
        elif difficulty <= 2:
            return "入门词汇：适合初学者"
        else:
            return "精选词汇：开启学习之旅"

    def is_cold_start_user(self, user_id: int, threshold: int = 10) -> bool:
        """判断用户是否为冷启动用户。

        Args:
            user_id: 用户ID。
            threshold: 学习记录阈值。

        Returns:
            bool: 是否为冷启动用户。
        """
        records = self.learning_records_crud.get_by_user(user_id)
        return len(records) < threshold


class RealtimePersonalizer:
    """实时个性化模块。

    根据用户当前会话行为实时调整推荐。
    """

    def __init__(self) -> None:
        """初始化实时个性化模块。"""
        self.config = RECOMMENDATION_CONFIG["realtime_personalization"]

        # 会话缓存 {user_id: session_data}
        self._session_cache: Dict[int, Dict[str, any]] = {}

        # 近期行为缓存
        self._recent_behavior_cache: Dict[int, Dict[str, any]] = {}

    def update_session(
        self, user_id: int, word_id: int, is_correct: bool, response_time: float, difficulty: int
    ) -> None:
        """更新用户会话数据。

        Args:
            user_id: 用户ID。
            word_id: 单词ID。
            is_correct: 是否正确。
            response_time: 响应时间（秒）。
            difficulty: 难度等级。
        """
        if user_id not in self._session_cache:
            self._session_cache[user_id] = {
                "words": [],
                "correct_count": 0,
                "total_time": 0,
                "start_time": datetime.now(),
            }

        session = self._session_cache[user_id]
        session["words"].append(
            {
                "word_id": word_id,
                "is_correct": is_correct,
                "response_time": response_time,
                "difficulty": difficulty,
                "timestamp": datetime.now(),
            }
        )

        if is_correct:
            session["correct_count"] += 1
        session["total_time"] += response_time

    def get_session_adjusted_difficulty(self, user_id: int) -> int:
        """根据会话表现动态调整推荐难度。

        Args:
            user_id: 用户ID。

        Returns:
            int: 建议难度等级（1-6）。
        """
        if user_id not in self._session_cache:
            return 3  # 默认中等难度

        session = self._session_cache[user_id]
        words = session["words"]

        if len(words) < 3:
            return 3

        # 计算正确率
        accuracy = session["correct_count"] / len(words)

        # 计算平均响应时间
        avg_time = session["total_time"] / len(words)

        # 计算近期正确率趋势（最近5个词）
        recent_words = words[-5:]
        recent_accuracy = sum(1 for w in recent_words if w["is_correct"]) / len(recent_words)

        # 计算当前平均难度
        avg_difficulty = sum(w["difficulty"] for w in words) / len(words)

        # 动态调整
        if accuracy > 0.8 and recent_accuracy > 0.8 and avg_time < 10:
            # 表现优秀，提升难度
            return min(6, int(avg_difficulty) + 1)
        elif accuracy < 0.5 or recent_accuracy < 0.4:
            # 表现较差，降低难度
            return max(1, int(avg_difficulty) - 1)
        else:
            return int(round(avg_difficulty))

    def get_realtime_preferences(self, user_id: int) -> Dict[str, any]:
        """获取用户实时偏好。

        Args:
            user_id: 用户ID。

        Returns:
            Dict[str, any]: 偏好信息，包含 preferred_difficulty、performance_trend、
                fatigue_level、engagement_level 等字段。
        """
        preferences = {
            "preferred_difficulty": 3,
            "performance_trend": "stable",
            "fatigue_level": "normal",
            "engagement_level": "normal",
        }

        if user_id not in self._session_cache:
            return preferences

        session = self._session_cache[user_id]
        words = session["words"]

        if len(words) < 3:
            return preferences

        # 性能趋势
        if len(words) >= 6:
            first_half = words[: len(words) // 2]
            second_half = words[len(words) // 2 :]
            first_acc = sum(1 for w in first_half if w["is_correct"]) / len(first_half)
            second_acc = sum(1 for w in second_half if w["is_correct"]) / len(second_half)

            if second_acc > first_acc + 0.1:
                preferences["performance_trend"] = "improving"
            elif second_acc < first_acc - 0.1:
                preferences["performance_trend"] = "declining"

        # 疲劳度（基于响应时间趋势）
        if len(words) >= 5:
            recent_times = [w["response_time"] for w in words[-5:]]
            earlier_times = (
                [w["response_time"] for w in words[-10:-5]]
                if len(words) >= 10
                else [w["response_time"] for w in words[:5]]
            )

            if (
                sum(recent_times) / len(recent_times)
                > sum(earlier_times) / len(earlier_times) * 1.5
            ):
                preferences["fatigue_level"] = "high"

        # 参与度（基于连续学习数量）
        session_duration = (datetime.now() - session["start_time"]).seconds / 60
        if len(words) > 10 and session_duration < 10:
            preferences["engagement_level"] = "high"
        elif len(words) < 5 and session_duration > 5:
            preferences["engagement_level"] = "low"

        preferences["preferred_difficulty"] = self.get_session_adjusted_difficulty(user_id)

        return preferences

    def adjust_recommendation_score(self, word: Dict[str, any], user_id: int) -> float:
        """根据实时偏好调整推荐分数。

        Args:
            word: 单词信息。
            user_id: 用户ID。

        Returns:
            float: 调整后的分数，范围 [0, 1]。
        """
        base_score = word.get("recommendation_score", 0.5)
        preferences = self.get_realtime_preferences(user_id)

        adjustment = 1.0

        # 难度匹配调整
        word_difficulty = word.get("difficulty_level", 3)
        preferred_diff = preferences["preferred_difficulty"]
        diff_match = 1 - abs(word_difficulty - preferred_diff) / 5
        adjustment *= 0.7 + diff_match * 0.3

        # 疲劳度调整（疲劳时降低高难度词分数）
        if preferences["fatigue_level"] == "high" and word_difficulty > 4:
            adjustment *= 0.8

        # 趋势调整（进步中时略微提升难度词分数）
        if preferences["performance_trend"] == "improving" and word_difficulty > preferred_diff:
            adjustment *= 1.1

        return min(1.0, base_score * adjustment)

    def clear_session(self, user_id: int) -> None:
        """清除会话数据。

        Args:
            user_id: 用户ID。
        """
        if user_id in self._session_cache:
            del self._session_cache[user_id]

    def end_session_and_learn(self, user_id: int) -> Dict[str, any]:
        """结束会话并返回学习摘要。

        Args:
            user_id: 用户ID。

        Returns:
            Dict[str, any]: 会话摘要，包含 total_words、correct_count、accuracy 等字段。
        """
        if user_id not in self._session_cache:
            return {}

        session = self._session_cache[user_id]
        words = session["words"]

        summary = {
            "total_words": len(words),
            "correct_count": session["correct_count"],
            "accuracy": session["correct_count"] / len(words) if words else 0,
            "avg_time": session["total_time"] / len(words) if words else 0,
            "duration_minutes": (datetime.now() - session["start_time"]).seconds / 60,
            "final_difficulty": self.get_session_adjusted_difficulty(user_id),
            "preferences": self.get_realtime_preferences(user_id),
        }

        # 保存到近期行为缓存
        self._recent_behavior_cache[user_id] = {
            "last_session": summary,
            "last_updated": datetime.now(),
        }

        return summary


# 导出所有类
__all__ = [
    "CollaborativeFiltering",
    "DynamicWeightAdjuster",
    "DiversityController",
    "ColdStartHandler",
    "RealtimePersonalizer",
]
