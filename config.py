"""
SmartVocab 智能词汇学习系统 - 配置文件
包含应用、学习、推荐算法等核心配置参数
"""

# 应用配置
APP_CONFIG = {
    "debug": True,              # 调试模式
    "port": 5000,               # 服务端口
    "host": "0.0.0.0"          # 服务主机地址
}

# 学习配置
LEARNING_CONFIG = {
    "default_daily_words": 20,          # 默认每日学习单词数
    "default_review_interval": 1,       # 默认复习间隔（天）
    "default_mastery_threshold": 0.8    # 默认掌握程度阈值
}

# 学习参数常量
LEARNING_PARAMS = {
    "default_word_count": 20,           # 默认学习单词数
    "default_test_word_count": 10,      # 默认测试单词数
    "default_review_limit": 20,         # 默认复习单词数
    "default_recommendation_limit": 10, # 默认推荐单词数
    "default_epochs": 50,               # 默认训练轮数
    "default_batch_size": 16,           # 默认批次大小
    "min_training_records": 50,         # 最小训练数据要求
    "max_word_length": 20,              # 最大单词长度（用于标准化）
    "max_translation_length": 100,      # 最大翻译长度（用于标准化）
    "max_learning_speed": 10,           # 最大学习速度（用于标准化）
    "max_review_std": 10,               # 最大复习标准差（用于标准化）
    "max_review_count": 10,             # 最大复习次数（用于限制增长倍数）
    "response_time_bonus": 10,           # 响应时间奖励阈值（秒）
    "response_time_penalty": 20,        # 响应时间惩罚阈值（秒）
    "strength_multiplier": 10,           # 强度倍数（用于遗忘曲线）
    "frequency_threshold": 100,         # 词频阈值
    "days_trend_analysis": 30,           # 趋势分析天数
    "urgency_base": 500,                # 紧急程度基础值
    "urgency_multiplier": 10            # 紧急程度倍数
}

# 推荐算法配置
RECOMMENDATION_CONFIG = {
    "max_recommendations": 50,          # 最大推荐数量
    "min_score_threshold": 0.3          # 最小推荐分数阈值
}

# 遗忘曲线配置
FORGETTING_CURVE_CONFIG = {
    "base_interval": 1,         # 基础复习间隔（天）
    "max_interval": 30,         # 最大复习间隔（天）
    "forgetting_rate": 0.5      # 遗忘率
}
