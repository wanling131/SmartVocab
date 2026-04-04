"""
测试推荐系统增强模块
"""
import sys
import os

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

# 设置环境变量跳过模型加载
os.environ["SMARTVOCAB_SKIP_DL_INIT"] = "1"

# 测试导入
try:
    from core.recommendation import RecommendationEngine
    from core.recommendation.recommendation_enhancements import (
        CollaborativeFiltering,
        DynamicWeightAdjuster,
        DiversityController,
        ColdStartHandler,
        RealtimePersonalizer
    )
    print("所有模块导入成功!")
    print("RecommendationEngine:", RecommendationEngine)
    print("CollaborativeFiltering:", CollaborativeFiltering)
    print("DynamicWeightAdjuster:", DynamicWeightAdjuster)
    print("DiversityController:", DiversityController)
    print("ColdStartHandler:", ColdStartHandler)
    print("RealtimePersonalizer:", RealtimePersonalizer)

except Exception as e:
    print(f"导入失败: {e}")
    import traceback
    traceback.print_exc()
