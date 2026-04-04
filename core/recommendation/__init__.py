"""
智能推荐子系统：多策略融合（难度/词频/历史/随机探索/深度学习）；PyTorch 见 requirements.txt，深度学习路径失败时回退传统策略。
"""

from .recommendation_engine import RecommendationEngine

__all__ = ["RecommendationEngine"]
