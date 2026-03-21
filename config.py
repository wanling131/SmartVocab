"""
SmartVocab 智能词汇学习系统 - 配置文件
包含应用、学习、推荐算法等核心配置参数
"""

import logging
import os
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).resolve().parent / ".env")
except ImportError:
    pass


def _env_bool(key: str, default: bool = True) -> bool:
    v = os.getenv(key)
    if v is None:
        return default
    return v.lower() in ("1", "true", "yes", "on")


def _is_production() -> bool:
    """生产/预发布环境：用于关闭调试信息、收紧错误响应等。"""
    env = (os.getenv("APP_ENV") or os.getenv("FLASK_ENV") or "").lower()
    if env in ("production", "prod", "staging"):
        return True
    return _env_bool("APP_PRODUCTION", False)


def _cors_origins() -> list:
    """
    CORS 允许的来源。逗号分隔；空或 * 表示开发期允许任意来源（不推荐生产）。
    生产环境应设为前端完整 Origin，例如 https://app.example.com
    """
    raw = os.getenv("CORS_ORIGINS", "*").strip()
    if not raw or raw == "*":
        return ["*"]
    return [o.strip() for o in raw.split(",") if o.strip()]


# 先判定是否生产模式（供下列默认值使用）
_PRODUCTION = _is_production()

# 应用配置（可从环境变量覆盖）
APP_CONFIG = {
    "debug": _env_bool("APP_DEBUG", not _PRODUCTION),
    "port": int(os.getenv("APP_PORT", "5000")),
    "host": os.getenv("APP_HOST", "0.0.0.0"),
    "log_level": os.getenv("LOG_LEVEL", "INFO").upper(),
    "production": _PRODUCTION,
    # 是否在 API 错误响应中返回异常详情（生产环境默认关闭）
    "expose_error_details": _env_bool("EXPOSE_ERROR_DETAILS", not _PRODUCTION),
    "cors_origins": _cors_origins(),
    # 请求体最大长度（字节），防止过大 JSON 拖垮服务
    "max_content_length": int(os.getenv("MAX_CONTENT_LENGTH_MB", "16")) * 1024 * 1024,
}


def configure_logging() -> None:
    """
    配置根日志格式与级别。应在 main / 测试入口最早调用。
    """
    level_name = APP_CONFIG.get("log_level", "INFO")
    level = getattr(logging, level_name, logging.INFO)
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=level,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        logging.getLogger().setLevel(level)

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
