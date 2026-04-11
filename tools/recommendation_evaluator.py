"""
推荐算法评估工具
提供离线评估指标：准确率、召回率、覆盖率、多样性
"""

import logging
from collections import defaultdict
from datetime import datetime
from typing import Dict, List

from tools.learning_records_crud import LearningRecordsCRUD
from tools.words_crud import WordsCRUD

logger = logging.getLogger(__name__)


class RecommendationEvaluator:
    """推荐算法评估器"""

    def __init__(self):
        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()

    def evaluate_coverage(self, recommendations: List[Dict], total_words: int) -> float:
        """
        评估推荐覆盖率

        Args:
            recommendations: 推荐列表
            total_words: 总词数

        Returns:
            float: 覆盖率 (0-1)
        """
        if total_words == 0:
            return 0.0

        recommended_ids = {word["id"] for word in recommendations}
        return len(recommended_ids) / total_words

    def evaluate_diversity(self, recommendations: List[Dict]) -> Dict[str, float]:
        """
        评估推荐多样性

        Returns:
            Dict: 包含难度多样性、词性多样性、来源多样性
        """
        if not recommendations:
            return {"difficulty_diversity": 0, "pos_diversity": 0}

        # 难度分布
        difficulty_counts = defaultdict(int)
        pos_counts = defaultdict(int)

        for word in recommendations:
            difficulty_counts[word.get("difficulty_level", 0)] += 1
            pos_counts[word.get("pos", "unknown")] += 1

        # 计算熵作为多样性指标
        total = len(recommendations)

        def entropy(counts):
            import math

            return -sum((c / total) * math.log2(c / total) for c in counts.values() if c > 0)

        return {
            "difficulty_diversity": entropy(difficulty_counts),
            "pos_diversity": entropy(pos_counts),
            "difficulty_distribution": dict(difficulty_counts),
            "pos_distribution": dict(pos_counts),
        }

    def evaluate_novelty(self, recommendations: List[Dict], user_history: List[Dict]) -> float:
        """
        评估推荐新颖度（未学习词汇比例）

        Args:
            recommendations: 推荐列表
            user_history: 用户历史学习记录

        Returns:
            float: 新颖度 (0-1)
        """
        if not recommendations:
            return 0.0

        learned_ids = {record["word_id"] for record in user_history}
        recommended_ids = {word["id"] for word in recommendations}

        new_words = recommended_ids - learned_ids
        return len(new_words) / len(recommended_ids) if recommended_ids else 0.0

    def evaluate_personalization(
        self, user_id: int, recommendations: List[Dict]
    ) -> Dict[str, float]:
        """
        评估个性化程度

        Args:
            user_id: 用户ID
            recommendations: 推荐列表

        Returns:
            Dict: 个性化指标
        """
        # 获取用户学习偏好
        records = self.learning_records_crud.get_by_user(user_id)

        if not records:
            return {"personalization_score": 0.0}

        # 计算用户平均掌握度
        avg_mastery = sum(r.get("mastery_level", 0.5) for r in records) / len(records)

        # 计算用户偏好难度
        difficulty_sum = sum(r.get("difficulty_level", 3) for r in records)
        preferred_difficulty = difficulty_sum / len(records) if records else 3

        # 评估推荐是否符合用户水平
        rec_difficulties = [w.get("difficulty_level", 3) for w in recommendations]
        avg_rec_difficulty = (
            sum(rec_difficulties) / len(rec_difficulties) if rec_difficulties else 3
        )

        # 难度匹配度（越接近越好）
        difficulty_match = 1 - abs(preferred_difficulty - avg_rec_difficulty) / 6

        return {
            "personalization_score": difficulty_match,
            "user_preferred_difficulty": round(preferred_difficulty, 2),
            "recommended_avg_difficulty": round(avg_rec_difficulty, 2),
            "user_avg_mastery": round(avg_mastery, 2),
        }

    def full_evaluation(self, user_id: int, recommendations: List[Dict]) -> Dict:
        """
        完整评估

        Args:
            user_id: 用户ID
            recommendations: 推荐列表

        Returns:
            Dict: 完整评估报告
        """
        # 获取基础数据
        user_records = self.learning_records_crud.get_by_user(user_id)
        total_words_count = len(self.words_crud.list_all(limit=10000))

        # 各项评估
        coverage = self.evaluate_coverage(recommendations, total_words_count)
        diversity = self.evaluate_diversity(recommendations)
        novelty = self.evaluate_novelty(recommendations, user_records)
        personalization = self.evaluate_personalization(user_id, recommendations)

        # 综合评分（加权平均）
        weights = {"coverage": 0.2, "diversity": 0.25, "novelty": 0.25, "personalization": 0.3}

        overall_score = (
            coverage * weights["coverage"]
            + (diversity["difficulty_diversity"] / 3) * weights["diversity"]  # 归一化
            + novelty * weights["novelty"]
            + personalization["personalization_score"] * weights["personalization"]
        )

        return {
            "overall_score": round(overall_score, 3),
            "coverage": round(coverage, 3),
            "diversity": diversity,
            "novelty": round(novelty, 3),
            "personalization": personalization,
            "recommendation_count": len(recommendations),
            "timestamp": datetime.now().isoformat(),
        }

    def compare_algorithms(self, user_id: int, algorithms: List[str] = None) -> Dict:
        """
        比较不同算法效果

        Args:
            user_id: 用户ID
            algorithms: 要比较的算法列表

        Returns:
            Dict: 各算法评估结果
        """
        from core.recommendation.recommendation_engine import RecommendationEngine

        if algorithms is None:
            algorithms = ["mixed", "difficulty", "frequency", "collaborative", "random"]

        engine = RecommendationEngine()
        results = {}

        for algo in algorithms:
            try:
                recs = engine.get_recommendations(user_id, limit=20, algorithm=algo)
                evaluation = self.full_evaluation(user_id, recs)
                results[algo] = evaluation
            except Exception as e:
                logger.error(f"算法 {algo} 评估失败: {e}")
                results[algo] = {"error": str(e)}

        return results


def main():
    """命令行入口"""
    import argparse
    import json

    parser = argparse.ArgumentParser(description="推荐算法评估工具")
    parser.add_argument("--user", type=int, required=True, help="用户ID")
    parser.add_argument("--compare", action="store_true", help="比较所有算法")
    parser.add_argument("--algorithm", type=str, default="mixed", help="指定算法")

    args = parser.parse_args()

    evaluator = RecommendationEvaluator()

    if args.compare:
        results = evaluator.compare_algorithms(args.user)
    else:
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        recs = engine.get_recommendations(args.user, limit=20, algorithm=args.algorithm)
        results = evaluator.full_evaluation(args.user, recs)

    print(json.dumps(results, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
