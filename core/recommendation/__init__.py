"""
智能推荐子系统：多策略融合（难度/词频/历史/随机探索/深度学习）；PyTorch 见 requirements.txt，深度学习路径失败时回退传统策略。

增强功能：
- 协同过滤（用户/物品）
- 动态权重调整
- 多样性控制（MMR）
- 冷启动策略
- 实时个性化
"""

from .recommendation_engine import RecommendationEngine

# 尝试导出增强模块
try:
    from .recommendation_enhancements import (
        CollaborativeFiltering,
        DynamicWeightAdjuster,
        DiversityController,
        ColdStartHandler,
        RealtimePersonalizer
    )
    __all__ = [
        "RecommendationEngine",
        "CollaborativeFiltering",
        "DynamicWeightAdjuster",
        "DiversityController",
        "ColdStartHandler",
        "RealtimePersonalizer"
    ]
except ImportError:
    __all__ = ["RecommendationEngine"]
