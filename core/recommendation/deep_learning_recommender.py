"""
深度学习推荐系统
使用神经网络进行词汇学习推荐
"""

import logging
import math
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

import json
from datetime import datetime, timedelta
from typing import Dict, List

import numpy as np

# 深度学习相关导入
try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, Dataset

    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    logging.getLogger(__name__).warning("PyTorch未安装，使用传统推荐算法")

# 导入配置常量
from config import LEARNING_PARAMS, RECOMMENDATION_CONFIG
from tools.learning_records_crud import LearningRecordsCRUD
from tools.recommendations_crud import RecommendationsCRUD
from tools.users_crud import UsersCRUD
from tools.words_crud import WordsCRUD

logger = logging.getLogger(__name__)


def _skip_heavy_dl_init() -> bool:
    """自动化自检或单元测试时可设 SMARTVOCAB_SKIP_DL_INIT=1，跳过模型加载与自动训练（避免耗时）。"""
    return os.environ.get("SMARTVOCAB_SKIP_DL_INIT", "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


# 训练参数常量
MIN_TRAINING_RECORDS = LEARNING_PARAMS["min_training_records"]

# 模型版本常量（用于兼容性检查）
MODEL_VERSION = "v2"  # 当前版本：LayerNorm + 25维特征
MODEL_FEATURE_DIM = 25  # 当前特征维度


class VocabularyDataset(Dataset):
    """词汇学习数据集"""

    def __init__(self, user_records, word_features, user_features, word_dim=25, user_dim=25):
        self.user_records = user_records
        self.word_features = word_features
        self.user_features = user_features
        self.word_dim = word_dim
        self.user_dim = user_dim

    def __len__(self):
        return len(self.user_records)

    def __getitem__(self, idx):
        record = self.user_records[idx]
        word_id = record["word_id"]
        user_id = record["user_id"]

        # 安全获取特征，如果不存在则使用默认值
        word_feature = self.word_features.get(word_id, [0.0] * self.word_dim)
        user_feature = self.user_features.get(user_id, [0.0] * self.user_dim)
        label = record["mastery_level"]

        # 确保特征维度正确
        if len(word_feature) != self.word_dim:
            word_feature = word_feature[: self.word_dim] + [0.0] * max(
                0, self.word_dim - len(word_feature)
            )
        if len(user_feature) != self.user_dim:
            user_feature = user_feature[: self.user_dim] + [0.0] * max(
                0, self.user_dim - len(user_feature)
            )

        return {
            "word_features": torch.FloatTensor(word_feature),
            "user_features": torch.FloatTensor(user_feature),
            "label": torch.FloatTensor([label]),
        }


class DeepLearningRecommender(nn.Module):
    """深度学习推荐模型 - 双塔架构 + 注意力机制"""

    def __init__(
        self, word_feature_dim, user_feature_dim, hidden_dims=[128, 64, 32], use_attention=True
    ):
        super(DeepLearningRecommender, self).__init__()

        self.use_attention = use_attention

        # 单词特征编码器（使用 LayerNorm 替代 BatchNorm 以支持小批量）
        self.word_encoder = nn.Sequential(
            nn.Linear(word_feature_dim, hidden_dims[0]),
            nn.LayerNorm(hidden_dims[0]),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dims[0], hidden_dims[1]),
            nn.LayerNorm(hidden_dims[1]),
            nn.ReLU(),
            nn.Dropout(0.2),
        )

        # 用户特征编码器
        self.user_encoder = nn.Sequential(
            nn.Linear(user_feature_dim, hidden_dims[0]),
            nn.LayerNorm(hidden_dims[0]),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dims[0], hidden_dims[1]),
            nn.LayerNorm(hidden_dims[1]),
            nn.ReLU(),
            nn.Dropout(0.2),
        )

        # 交叉注意力机制（用户对单词特征的注意力）
        if use_attention:
            self.attention = nn.MultiheadAttention(
                embed_dim=hidden_dims[1], num_heads=4, dropout=0.1, batch_first=True
            )
            # 上下文门控
            self.context_gate = nn.Sequential(
                nn.Linear(hidden_dims[1] * 3, hidden_dims[1]), nn.Sigmoid()
            )

        # 融合层（考虑注意力后的维度变化）
        fusion_input_dim = hidden_dims[1] * 3 if use_attention else hidden_dims[1] * 2
        self.fusion = nn.Sequential(
            nn.Linear(fusion_input_dim, hidden_dims[2]),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(hidden_dims[2], 1),
            nn.Sigmoid(),
        )

        # 辅助输出头（用于多任务学习：预测难度匹配度）
        self.aux_head = nn.Sequential(
            nn.Linear(hidden_dims[2], 16), nn.ReLU(), nn.Linear(16, 1), nn.Sigmoid()
        )

    def forward(self, word_features, user_features):
        # 编码
        word_encoded = self.word_encoder(word_features)  # [batch, hidden_dims[1]]
        user_encoded = self.user_encoder(user_features)  # [batch, hidden_dims[1]]

        if self.use_attention:
            # 为注意力机制准备输入 (seq_len=1)
            word_seq = word_encoded.unsqueeze(1)  # [batch, 1, hidden]
            user_seq = user_encoded.unsqueeze(1)  # [batch, 1, hidden]

            # 用户对单词的注意力
            attended_word, _ = self.attention(
                query=user_seq, key=word_seq, value=word_seq
            )  # [batch, 1, hidden]
            attended_word = attended_word.squeeze(1)  # [batch, hidden]

            # 单词对用户的注意力
            attended_user, _ = self.attention(
                query=word_seq, key=user_seq, value=user_seq
            )  # [batch, 1, hidden]
            attended_user = attended_user.squeeze(1)  # [batch, hidden]

            # 门控融合
            gate_input = torch.cat(
                [word_encoded, user_encoded, attended_word * attended_user], dim=1
            )
            gate = self.context_gate(gate_input)

            # 融合所有特征
            combined = torch.cat(
                [word_encoded * gate, user_encoded * gate, attended_word * attended_user], dim=1
            )
        else:
            combined = torch.cat([word_encoded, user_encoded], dim=1)

        # 主输出
        output = self.fusion(combined)

        return output

    def get_embeddings(self, word_features, user_features):
        """
        获取单词和用户的嵌入向量（用于相似度计算）
        """
        word_encoded = self.word_encoder(word_features)
        user_encoded = self.user_encoder(user_features)
        return word_encoded, user_encoded


class DeepLearningRecommendationEngine:
    """
    基于深度学习的推荐引擎
    使用单例模式避免重复初始化
    实现分层模型管理：通用模型 + 用户特定模型
    """

    _instance = None
    _initialized = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DeepLearningRecommendationEngine, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """
        初始化深度学习推荐引擎
        """
        # 避免重复初始化
        if DeepLearningRecommendationEngine._initialized:
            return

        self.learning_records_crud = LearningRecordsCRUD()
        self.words_crud = WordsCRUD()
        self.recommendations_crud = RecommendationsCRUD()
        self.users_crud = UsersCRUD()

        # 模型相关
        self.model = None
        self.word_features = {}
        self.user_features = {}
        self.word_id_to_index = {}
        self.user_id_to_index = {}
        self.is_trained = False

        # 特征维度（增强版）- 从配置读取
        dl_config = RECOMMENDATION_CONFIG.get("deep_learning_enhanced", {})
        self.word_feature_dim = dl_config.get("word_feature_dim", 25)  # 单词特征维度（增强）
        self.user_feature_dim = dl_config.get("user_feature_dim", 25)  # 用户特征维度（增强）
        self.use_attention = dl_config.get("attention_enabled", True)  # 注意力机制

        if TORCH_AVAILABLE:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
            logger.info(f"使用设备: {self.device}")

            if _skip_heavy_dl_init():
                logger.info(
                    "SMARTVOCAB_SKIP_DL_INIT 已启用：跳过深度学习模型加载与自动训练（推荐将回退传统策略）"
                )
            else:
                # 启动时只加载通用模型
                self._try_load_model()
                # 如果没有已训练的模型，尝试自动训练
                if not self.is_trained:
                    logger.info("未找到已训练的模型，尝试自动训练...")
                    self._auto_train_model()
        else:
            logger.info("使用传统推荐算法")

        # 标记为已初始化
        DeepLearningRecommendationEngine._initialized = True

    def _try_load_model(self, user_id=None):
        """尝试加载已训练的模型"""
        logger.debug("=== 模型加载开始 ===")
        logger.debug(f"目标用户ID: {user_id if user_id else '通用模型'}")

        model_paths = []

        # 如果指定了用户ID，优先尝试加载用户特定模型
        if user_id is not None:
            user_model_path = f"models/deep_learning_recommender_user_{user_id}.pth"
            model_paths.append(user_model_path)
            logger.debug(f"1. 检查用户特定模型: {user_model_path}")

        # 然后尝试通用模型
        common_model_paths = [
            "models/deep_learning_recommender.pth",
            "deep_learning_recommender.pth",
            "../models/deep_learning_recommender.pth",
        ]
        model_paths.extend(common_model_paths)

        logger.debug("2. 检查通用模型路径:")
        for i, path in enumerate(common_model_paths, 2):
            logger.debug(f"   {i}. {path}")

        for i, model_path in enumerate(model_paths, 1):
            try:
                if os.path.exists(model_path):
                    logger.debug(f"[OK] 找到模型文件: {model_path}")
                    success = self.load_model(model_path)
                    if success:
                        model_type = (
                            "用户特定" if user_id and f"user_{user_id}" in model_path else "通用"
                        )
                        logger.debug(f"[OK] 成功加载{model_type}模型: {model_path}")
                        logger.debug("=== 模型加载完成 ===")
                        return True
                    else:
                        logger.warning(f"[FAIL] 模型文件存在但加载失败: {model_path}")
                else:
                    logger.warning(f"[FAIL] 模型文件不存在: {model_path}")
            except Exception as e:
                logger.warning(f"[FAIL] 加载模型异常 {model_path}: {str(e)}")
                continue

        logger.warning("[FAIL] 所有模型路径都加载失败")
        logger.debug("=== 模型加载结束 ===")
        return False

    def _auto_train_model(self):
        """自动训练模型"""
        try:
            # 检查是否有足够的训练数据
            all_records = self.learning_records_crud.list_all(limit=10000)  # 获取更多记录
            if len(all_records) >= MIN_TRAINING_RECORDS:  # 至少需要50条记录
                logger.info("检测到足够的学习数据，开始自动训练模型...")
                success = self.train_model(
                    epochs=LEARNING_PARAMS["default_epochs"],
                    batch_size=LEARNING_PARAMS["default_batch_size"],
                    learning_rate=0.001,
                )
                if success:
                    logger.info("模型自动训练完成！")
                    # 保存模型
                    os.makedirs("models", exist_ok=True)
                    self.save_model("models/deep_learning_recommender.pth")
                else:
                    logger.warning("模型自动训练失败")
            else:
                logger.info(
                    f"训练数据不足 ({len(all_records)} 条)，需要至少{MIN_TRAINING_RECORDS}条记录"
                )
        except Exception as e:
            logger.error(f"自动训练模型时出错: {str(e)}")

    def extract_word_features(self, word_data):
        """
        提取单词特征（增强版：25维特征向量）

        Args:
            word_data (dict): 单词数据

        Returns:
            list: 单词特征向量
        """
        features = []

        # === 基础特征 (8维) ===
        # 难度等级 (归一化)
        features.append(word_data.get("difficulty_level", 3) / 6.0)

        # 词频排名 (对数归一化)
        freq_rank = word_data.get("frequency_rank", 1000)
        features.append(min(1.0, math.log(freq_rank + 1) / 10))

        # CEFR标准编码 (one-hot)
        cefr_mapping = {"A1": 0, "A2": 1, "B1": 2, "B2": 3, "C1": 4, "C2": 5}
        cefr_level = cefr_mapping.get(word_data.get("cefr_standard", "B1"), 2)
        cefr_one_hot = [1 if i == cefr_level else 0 for i in range(6)]
        features.extend(cefr_one_hot)

        # 词性编码 (one-hot, 5维)
        pos_mapping = {
            "n": [1, 0, 0, 0, 0],
            "v": [0, 1, 0, 0, 0],
            "adj": [0, 0, 1, 0, 0],
            "adv": [0, 0, 0, 1, 0],
            "other": [0, 0, 0, 0, 1],
        }
        pos = word_data.get("pos", "other")
        pos_features = pos_mapping.get(pos, [0, 0, 0, 0, 1])
        features.extend(pos_features)

        # === 领域特征 (3维) ===
        domain_data = word_data.get("domain", "{}")
        if isinstance(domain_data, str):
            try:
                domain_data = json.loads(domain_data)
            except (json.JSONDecodeError, TypeError):
                domain_data = {}
        elif isinstance(domain_data, list):
            domain_data = {}

        features.append(domain_data.get("spoken_ratio", 0.5))
        features.append(domain_data.get("academic_ratio", 0.5))
        # 商业使用频率（新增）
        features.append(domain_data.get("business_ratio", 0.5))

        # === 词汇结构特征 (4维) ===
        word_text = word_data.get("word", "")
        # 单词长度（归一化）
        features.append(min(len(word_text) / LEARNING_PARAMS["max_word_length"], 1.0))
        # 音节数估计（基于元音数量）
        vowel_count = sum(1 for c in word_text.lower() if c in "aeiou")
        features.append(min(vowel_count / 5, 1.0))
        # 是否有音标
        phonetic = word_data.get("phonetic", "")
        features.append(1.0 if phonetic else 0.0)
        # 是否是复合词（包含连字符或空格）
        features.append(1.0 if "-" in word_text or " " in word_text else 0.0)

        # === 语义特征 (5维) ===
        translation = word_data.get("translation", "")
        # 翻译长度（归一化）
        features.append(min(len(translation) / LEARNING_PARAMS["max_translation_length"], 1.0))
        # 翻译中的逗号数量（多义词指标）
        comma_count = translation.count("，") + translation.count(",")
        features.append(min(comma_count / 3, 1.0))

        # 标签特征（考试类型）
        tag = word_data.get("tag", "")
        features.append(1.0 if "CET4" in tag or "四级" in tag else 0.0)
        features.append(1.0 if "CET6" in tag or "六级" in tag else 0.0)
        features.append(1.0 if "IELTS" in tag or "TOEFL" in tag or "GRE" in tag else 0.0)

        # 补充特征到固定维度
        while len(features) < self.word_feature_dim:
            features.append(0.0)

        return features[: self.word_feature_dim]

    def extract_user_features(self, user_id, user_records):
        """
        提取用户特征（增强版：25维特征向量，包含实时性和多样性特征）

        Args:
            user_id (int): 用户ID
            user_records (list): 用户学习记录

        Returns:
            list: 用户特征向量
        """
        features = []

        if not user_records:
            return [0.0] * self.user_feature_dim

        now = datetime.now()
        total_words = len(user_records)

        # === 学习统计特征 (7维) ===
        mastered_words = sum(1 for r in user_records if r.get("is_mastered", False))
        avg_mastery = sum(r.get("mastery_level", 0) for r in user_records) / total_words
        total_reviews = sum(r.get("review_count", 0) for r in user_records)

        features.append(total_words / 1000.0)  # 学习单词数 (标准化)
        features.append(mastered_words / max(total_words, 1))  # 掌握率
        features.append(avg_mastery)  # 平均掌握程度
        features.append(min(total_reviews / 1000.0, 1.0))  # 总复习次数 (标准化)
        features.append(min(total_reviews / max(total_words, 1) / 10.0, 1.0))  # 平均复习深度

        # 学习速度特征
        if user_records:
            first_learned = min(r.get("created_at", now) for r in user_records)
            days_learning = max((now - first_learned).days, 1)
            learning_speed = total_words / days_learning
            features.append(min(learning_speed / LEARNING_PARAMS["max_learning_speed"], 1.0))
        else:
            features.append(0.0)

        # 连续学习天数
        streak_days = self._calculate_streak(user_records)
        features.append(min(streak_days / 30.0, 1.0))  # 30天归一化

        # === 难度偏好特征 (4维) ===
        difficulty_levels = [
            r.get("difficulty_level", 3) for r in user_records if "difficulty_level" in r
        ]
        if difficulty_levels:
            avg_difficulty = sum(difficulty_levels) / len(difficulty_levels)
            features.append(avg_difficulty / 6.0)  # 平均难度偏好

            # 难度分布 (低/中/高)
            low_ratio = sum(1 for d in difficulty_levels if d <= 2) / len(difficulty_levels)
            mid_ratio = sum(1 for d in difficulty_levels if 3 <= d <= 4) / len(difficulty_levels)
            high_ratio = sum(1 for d in difficulty_levels if d >= 5) / len(difficulty_levels)
            features.extend([low_ratio, mid_ratio, high_ratio])
        else:
            features.extend([0.5, 0.3, 0.4, 0.3])  # 默认值

        # === 学习模式特征 (4维) ===
        # 近期活跃度（7天内）
        recent_records = [
            r
            for r in user_records
            if r.get("last_reviewed_at") and (now - r["last_reviewed_at"]).days <= 7
        ]
        recent_activity = len(recent_records) / max(total_words, 1)
        features.append(recent_activity)

        # 学习一致性（复习次数标准差的倒数）
        review_counts = [r.get("review_count", 0) for r in user_records]
        if review_counts and len(review_counts) > 1:
            review_std = np.std(review_counts)
            consistency = 1 / (1 + review_std / 5)  # 归一化
            features.append(consistency)
        else:
            features.append(0.5)

        # 学习时段偏好（简化：上午/下午/晚上）
        hour_distribution = [0, 0, 0]  # 0-8, 8-16, 16-24
        for r in user_records:
            if r.get("last_reviewed_at"):
                hour = r["last_reviewed_at"].hour
                if hour < 8:
                    hour_distribution[0] += 1
                elif hour < 16:
                    hour_distribution[1] += 1
                else:
                    hour_distribution[2] += 1

        total_time_slots = sum(hour_distribution) or 1
        features.extend([h / total_time_slots for h in hour_distribution])

        # === 实时表现特征 (4维) ===
        # 近7天正确率趋势
        recent_correct = sum(1 for r in recent_records if r.get("mastery_level", 0) > 0.5)
        recent_accuracy = recent_correct / len(recent_records) if recent_records else 0.5
        features.append(recent_accuracy)

        # 掌握速度（首次学习到掌握的平均时间）
        mastered_records = [r for r in user_records if r.get("is_mastered")]
        if mastered_records:
            mastery_speeds = []
            for r in mastered_records:
                if r.get("first_learned_at") and r.get("last_reviewed_at"):
                    days = (r["last_reviewed_at"] - r["first_learned_at"]).days
                    mastery_speeds.append(days)
            avg_mastery_days = sum(mastery_speeds) / len(mastery_speeds) if mastery_speeds else 7
            features.append(max(0, 1 - avg_mastery_days / 30))  # 30天归一化
        else:
            features.append(0.5)

        # 遗忘率估计（基于复习间隔和掌握度变化）
        forgetting_estimate = self._estimate_forgetting_rate(user_records)
        features.append(forgetting_estimate)

        # 学习强度（近期学习密度）
        learning_intensity = len(recent_records) / 7.0  # 每天学习数
        features.append(min(learning_intensity / 10.0, 1.0))  # 10词/天归一化

        # === 多样性偏好特征 (4维) ===
        # 词性多样性
        pos_set = set()
        for r in user_records:
            if r.get("pos"):
                pos_set.add(r["pos"])
        pos_diversity = len(pos_set) / 5.0  # 5种词性归一化
        features.append(pos_diversity)

        # 领域多样性（基于tag）
        tag_set = set()
        for r in user_records:
            if r.get("tag"):
                tags = r["tag"].split(",")
                tag_set.update(tags)
        tag_diversity = min(len(tag_set) / 10.0, 1.0)  # 10种标签归一化
        features.append(tag_diversity)

        # 难度跨度（学过的最高难度 - 最低难度）
        if difficulty_levels:
            difficulty_spread = (max(difficulty_levels) - min(difficulty_levels)) / 5.0
            features.append(difficulty_spread)
        else:
            features.append(0.0)

        # 新词探索意愿（最近学习的词中，低频词比例）
        low_freq_count = sum(1 for r in recent_records if r.get("frequency_rank", 1000) > 2000)
        exploration_will = low_freq_count / len(recent_records) if recent_records else 0
        features.append(exploration_will)

        # 补充特征到固定维度
        while len(features) < self.user_feature_dim:
            features.append(0.0)

        return features[: self.user_feature_dim]

    def _calculate_streak(self, user_records: List[Dict]) -> int:
        """
        计算用户连续学习天数
        """
        if not user_records:
            return 0

        # 收集所有学习日期
        dates = set()
        for r in user_records:
            if r.get("last_reviewed_at"):
                dates.add(r["last_reviewed_at"].date())

        if not dates:
            return 0

        # 计算连续天数
        sorted_dates = sorted(dates, reverse=True)
        today = datetime.now().date()
        streak = 0

        for i, date in enumerate(sorted_dates):
            expected_date = today - timedelta(days=i)
            if date == expected_date:
                streak += 1
            else:
                break

        return streak

    def _estimate_forgetting_rate(self, user_records: List[Dict]) -> float:
        """
        估计用户的遗忘率（基于艾宾浩斯曲线）
        """
        # 简化估计：基于复习次数和掌握度的关系
        if not user_records:
            return 0.5

        # 找出需要多次复习才能掌握的词的比例
        high_review_low_mastery = sum(
            1
            for r in user_records
            if r.get("review_count", 0) > 3 and r.get("mastery_level", 0) < 0.5
        )
        total = len(user_records)

        return high_review_low_mastery / total if total > 0 else 0.5

    def prepare_training_data(self):
        """
        准备训练数据
        """
        logger.info("准备训练数据...")

        # 获取所有学习记录
        all_records = self.learning_records_crud.list_all(limit=10000)  # 增加限制以获取更多记录

        # 获取所有单词和用户
        all_words = self.words_crud.list_all(limit=10000)  # 增加限制以获取更多单词
        all_users = set(record["user_id"] for record in all_records)

        # 构建索引映射
        self.word_id_to_index = {word["id"]: idx for idx, word in enumerate(all_words)}
        self.user_id_to_index = {user_id: idx for idx, user_id in enumerate(all_users)}

        logger.debug(f"单词总数: {len(all_words)}")
        logger.info(f"用户总数: {len(all_users)}")
        logger.debug(f"学习记录总数: {len(all_records)}")

        # 检查学习记录中的word_id是否存在于单词表中
        missing_words = []
        for record in all_records:
            word_id = record["word_id"]
            if word_id not in self.word_id_to_index:
                missing_words.append(word_id)

        if missing_words:
            logger.warning(f"发现 {len(missing_words)} 个学习记录中的word_id在单词表中不存在")
            logger.debug(f"缺失的word_id示例: {missing_words[:10]}")

        # 提取特征
        logger.info("提取单词特征...")
        for word in all_words:
            self.word_features[word["id"]] = self.extract_word_features(word)

        logger.info("提取用户特征...")
        for user_id in all_users:
            user_records = [r for r in all_records if r["user_id"] == user_id]
            self.user_features[user_id] = self.extract_user_features(user_id, user_records)

        # 准备训练数据
        training_records = []
        valid_count = 0
        invalid_count = 0

        for record in all_records:
            word_id = record["word_id"]
            user_id = record["user_id"]

            # 确保特征存在且有效
            if (
                word_id in self.word_features
                and user_id in self.user_features
                and len(self.word_features[word_id]) == self.word_feature_dim
                and len(self.user_features[user_id]) == self.user_feature_dim
            ):
                training_records.append(record)
                valid_count += 1
            else:
                invalid_count += 1
                # 详细分析无效原因
                reasons = []
                if word_id not in self.word_features:
                    reasons.append(f"word_id={word_id}不在单词表中")
                elif len(self.word_features[word_id]) != self.word_feature_dim:
                    reasons.append(
                        f"word_id={word_id}特征维度错误({len(self.word_features[word_id])})"
                    )

                if user_id not in self.user_features:
                    reasons.append(f"user_id={user_id}用户特征缺失")
                elif len(self.user_features[user_id]) != self.user_feature_dim:
                    reasons.append(
                        f"user_id={user_id}特征维度错误({len(self.user_features[user_id])})"
                    )

                logger.debug(
                    f"跳过无效记录: word_id={word_id}, user_id={user_id}, 原因: {', '.join(reasons)}"
                )

        logger.info(f"训练数据准备完成: {valid_count} 条有效记录, {invalid_count} 条无效记录")
        logger.debug(f"有效记录比例: {valid_count/(valid_count+invalid_count)*100:.1f}%")
        return training_records

    def check_and_train_model(self, user_id):
        """
        检查用户学习记录数量，如果超过50个则训练模型

        Args:
            user_id (int): 用户ID

        Returns:
            bool: 是否成功训练或加载模型
        """
        try:
            # 获取用户学习记录数量
            user_records = self.learning_records_crud.get_by_user(user_id)
            record_count = len(user_records)

            logger.info(f"用户 {user_id} 当前学习记录数量: {record_count}")

            # 检查是否已经有模型文件名
            model_filename = self.users_crud.get_model_filename(user_id)

            if model_filename:
                # 检查模型文件是否存在
                model_path = f"models/{model_filename}"
                if os.path.exists(model_path):
                    logger.debug(f"找到用户 {user_id} 的模型文件: {model_filename}")
                    success = self.load_model(model_path)
                    if success:
                        return True
                    else:
                        logger.warning("加载用户失败，将重新训练")

            # 如果学习记录超过最小要求，训练新模型
            if record_count >= MIN_TRAINING_RECORDS:
                logger.info(
                    f"用户 {user_id} 学习记录超过{MIN_TRAINING_RECORDS}个，开始训练深度学习模型..."
                )
                success = self.train_model_for_user(
                    user_id,
                    epochs=LEARNING_PARAMS["default_epochs"],
                    batch_size=LEARNING_PARAMS["default_batch_size"],
                )

                if success:
                    # 保存模型文件名到数据库
                    model_filename = f"deep_learning_recommender_user_{user_id}.pth"
                    self.users_crud.update_model_filename(user_id, model_filename)
                    logger.info(f"用户 {user_id} 的模型训练完成，文件名已保存到数据库")
                    return True
                else:
                    logger.info(f"用户 {user_id} 的模型训练失败")
                    return False
            else:
                logger.info(f"用户 {user_id} 学习记录不足{MIN_TRAINING_RECORDS}个，暂不训练模型")
                return False

        except Exception as e:
            logger.error(f"检查并训练模型时出错: {str(e)}")
            return False

    def train_model_for_user(
        self,
        user_id,
        epochs=LEARNING_PARAMS["default_epochs"],
        batch_size=LEARNING_PARAMS["default_batch_size"],
        learning_rate=0.001,
    ):
        """
        为特定用户训练模型

        Args:
            user_id (int): 用户ID
            epochs (int): 训练轮数
            batch_size (int): 批次大小
            learning_rate (float): 学习率

        Returns:
            bool: 训练是否成功
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch未安装，无法训练模型")
            return False

        try:
            logger.info(f"为用户 {user_id} 训练深度学习模型...")

            # 获取该用户的学习记录
            user_records = self.learning_records_crud.get_by_user(user_id)
            if len(user_records) < MIN_TRAINING_RECORDS:
                logger.info(
                    f"用户 {user_id} 的学习记录不足 ({len(user_records)} 条)，需要至少{MIN_TRAINING_RECORDS}条记录"
                )
                return False

            # 获取所有单词数据
            all_words = self.words_crud.list_all()
            if not all_words:
                logger.warning("没有找到单词数据")
                return False

            # 构建特征
            self.word_features = {}
            self.user_features = {}
            self.word_id_to_index = {}
            self.user_id_to_index = {}

            # 构建单词特征
            for i, word in enumerate(all_words):
                word_id = word["id"]
                self.word_features[word_id] = self.extract_word_features(word)
                self.word_id_to_index[word_id] = i

            # 构建用户特征
            self.user_features[user_id] = self.extract_user_features(user_id, user_records)
            self.user_id_to_index[user_id] = 0

            logger.debug(
                f"特征构建完成: 单词特征 {len(self.word_features)} 个, 用户特征 {len(self.user_features)} 个"
            )

            # 创建数据集
            dataset = VocabularyDataset(user_records, self.word_features, self.user_features)
            dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

            # 创建模型
            self.model = DeepLearningRecommender(self.word_feature_dim, self.user_feature_dim).to(
                self.device
            )

            # 优化器和损失函数
            optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)
            criterion = nn.MSELoss()

            # 训练
            self.model.train()
            for epoch in range(epochs):
                total_loss = 0
                for batch in dataloader:
                    word_features = batch["word_features"].to(self.device)
                    user_features = batch["user_features"].to(self.device)
                    labels = batch["label"].to(self.device)

                    optimizer.zero_grad()
                    outputs = self.model(word_features, user_features)
                    loss = criterion(outputs, labels)
                    loss.backward()
                    optimizer.step()

                    total_loss += loss.item()

                if epoch % 10 == 0:
                    avg_loss = total_loss / len(dataloader)
                    logger.debug(f"Epoch {epoch}, 平均损失: {avg_loss:.4f}")

            self.is_trained = True
            logger.info(f"用户 {user_id} 的模型训练完成！")

            # 保存用户特定模型
            self.save_model(user_id=user_id)

            return True

        except Exception as e:
            logger.error(f"训练模型失败: {str(e)}")
            import traceback

            traceback.print_exc()
            return False

    def train_model(
        self,
        epochs=LEARNING_PARAMS["default_epochs"],
        batch_size=LEARNING_PARAMS["default_batch_size"],
        learning_rate=0.001,
    ):
        """
        训练深度学习模型

        Args:
            epochs (int): 训练轮数
            batch_size (int): 批次大小
            learning_rate (float): 学习率
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch未安装，无法训练深度学习模型")
            return False

        logger.info("开始训练深度学习推荐模型...")

        # 准备数据
        training_records = self.prepare_training_data()
        if len(training_records) < MIN_TRAINING_RECORDS:
            logger.info(
                f"训练数据不足 ({len(training_records)} 条)，需要至少{MIN_TRAINING_RECORDS}条记录"
            )
            return False

        # 创建数据集
        dataset = VocabularyDataset(training_records, self.word_features, self.user_features)

        # 创建数据加载器
        dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)

        # 初始化模型
        self.model = DeepLearningRecommender(self.word_feature_dim, self.user_feature_dim).to(
            self.device
        )

        # 定义损失函数和优化器
        criterion = nn.MSELoss()
        optimizer = optim.Adam(self.model.parameters(), lr=learning_rate)

        # 训练循环
        self.model.train()
        for epoch in range(epochs):
            total_loss = 0
            for batch in dataloader:
                word_features = batch["word_features"].to(self.device)
                user_features = batch["user_features"].to(self.device)
                labels = batch["label"].to(self.device)

                # 前向传播
                optimizer.zero_grad()
                outputs = self.model(word_features, user_features)
                loss = criterion(outputs, labels)

                # 反向传播
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            if epoch % 10 == 0:
                avg_loss = total_loss / len(dataloader)
                logger.debug(f"Epoch {epoch}, Loss: {avg_loss:.4f}")

        self.is_trained = True
        logger.info("模型训练完成!")
        return True

    def get_deep_learning_recommendations(
        self, user_id, limit=LEARNING_PARAMS["default_recommendation_limit"]
    ):
        """
        使用深度学习模型获取推荐

        Args:
            user_id (int): 用户ID
            limit (int): 推荐数量

        Returns:
            list: 推荐单词列表
        """
        if not self.is_trained or not TORCH_AVAILABLE:
            logger.info("深度学习模型未训练或PyTorch未安装，使用传统推荐")
            return self._get_traditional_recommendations(user_id, limit)

        # 获取用户已学单词
        user_records = self.learning_records_crud.get_by_user(user_id)
        learned_word_ids = {record["word_id"] for record in user_records}

        # 获取用户特征
        if user_id not in self.user_features:
            self.user_features[user_id] = self.extract_user_features(user_id, user_records)

        user_feature = torch.FloatTensor(self.user_features[user_id]).unsqueeze(0).to(self.device)

        # 获取所有候选单词
        all_words = self.words_crud.list_all(limit=500)
        candidates = []

        self.model.eval()
        with torch.no_grad():
            for word in all_words:
                if word["id"] in learned_word_ids:
                    continue

                if word["id"] not in self.word_features:
                    continue

                word_feature = (
                    torch.FloatTensor(self.word_features[word["id"]]).unsqueeze(0).to(self.device)
                )

                # 预测掌握程度
                predicted_mastery = self.model(word_feature, user_feature).item()

                candidates.append(
                    {
                        "id": word["id"],
                        "word": word["word"],
                        "translation": word["translation"],
                        "difficulty_level": word["difficulty_level"],
                        "recommendation_score": predicted_mastery,
                        "algorithm_type": "deep_learning",
                    }
                )

        # 按推荐分数排序
        candidates.sort(key=lambda x: x["recommendation_score"], reverse=True)

        return candidates[:limit]

    def _get_traditional_recommendations(self, user_id, limit):
        """
        传统推荐算法（备用）
        """
        # 简单的基于难度的推荐
        user_records = self.learning_records_crud.get_by_user(user_id)
        learned_word_ids = {record["word_id"] for record in user_records}

        if not user_records:
            target_difficulty = 1
        else:
            avg_mastery = sum(r.get("mastery_level", 0) for r in user_records) / len(user_records)
            if avg_mastery < 0.3:
                target_difficulty = 1
            elif avg_mastery < 0.6:
                target_difficulty = 2
            else:
                target_difficulty = 3

        words = self.words_crud.get_by_difficulty(target_difficulty)
        candidates = [w for w in words if w["id"] not in learned_word_ids]

        return [
            {
                "id": w["id"],
                "word": w["word"],
                "translation": w["translation"],
                "difficulty_level": w["difficulty_level"],
                "recommendation_score": 0.5,
                "algorithm_type": "traditional",
            }
            for w in candidates[:limit]
        ]

    def save_model(self, filepath=None, user_id=None):
        """
        保存模型

        Args:
            filepath (str): 保存路径，如果为None则自动生成
            user_id (int): 用户ID，如果指定则为该用户保存独立模型
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch未安装，无法保存模型")
            return False

        if not self.is_trained:
            logger.warning("模型未训练，无法保存")
            return False

        try:
            # 如果指定了用户ID，为特定用户保存模型
            if user_id is not None:
                if filepath is None:
                    filepath = f"models/deep_learning_recommender_user_{user_id}.pth"
                logger.info(f"为用户 {user_id} 保存模型到: {filepath}")
            else:
                if filepath is None:
                    filepath = "models/deep_learning_recommender.pth"
                logger.info(f"保存通用模型到: {filepath}")

            # 确保目录存在
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            checkpoint = {
                "model_version": MODEL_VERSION,  # 版本标识
                "model_state_dict": self.model.state_dict(),
                "word_features": self.word_features,
                "user_features": self.user_features,
                "word_id_to_index": self.word_id_to_index,
                "user_id_to_index": self.user_id_to_index,
                "word_feature_dim": self.word_feature_dim,
                "user_feature_dim": self.user_feature_dim,
                "user_id": user_id,  # 记录是为哪个用户保存的
            }

            torch.save(checkpoint, filepath)
            logger.info(f"模型已保存到: {filepath}")
            return True
        except Exception as e:
            logger.error(f"保存模型失败: {str(e)}")
            return False

    def load_model(self, filepath):
        """
        加载模型（含版本兼容性检查）

        不兼容的旧版本模型会被自动删除，返回 False 触发重新训练。
        """
        if not TORCH_AVAILABLE:
            logger.warning("PyTorch未安装，无法加载模型")
            return False

        try:
            # PyTorch 2.6+ 默认 weights_only=True，旧 checkpoint 需显式关闭（本地可信模型文件）
            try:
                checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)
            except TypeError:
                checkpoint = torch.load(filepath, map_location=self.device)

            # 版本兼容性检查
            saved_version = checkpoint.get("model_version", "v1")  # 旧文件默认 v1
            saved_dim = checkpoint.get("word_feature_dim", 20)  # 旧文件默认 20维

            if saved_version != MODEL_VERSION or saved_dim != MODEL_FEATURE_DIM:
                logger.warning(
                    f"模型版本不兼容: 文件版本={saved_version}/{saved_dim}维, "
                    f"当前版本={MODEL_VERSION}/{MODEL_FEATURE_DIM}维"
                )
                logger.info(f"删除不兼容的旧模型文件: {filepath}")
                try:
                    os.remove(filepath)
                except OSError as e:
                    logger.warning(f"删除旧模型文件失败: {e}")
                return False  # 返回 False，触发重新训练

            self.word_features = checkpoint["word_features"]
            self.user_features = checkpoint["user_features"]
            self.word_id_to_index = checkpoint["word_id_to_index"]
            self.user_id_to_index = checkpoint["user_id_to_index"]
            self.word_feature_dim = checkpoint["word_feature_dim"]
            self.user_feature_dim = checkpoint["user_feature_dim"]

            self.model = DeepLearningRecommender(self.word_feature_dim, self.user_feature_dim).to(
                self.device
            )
            self.model.load_state_dict(checkpoint["model_state_dict"])

            self.is_trained = True
            logger.info(f"模型已从 {filepath} 加载 (版本={MODEL_VERSION})")
            return True
        except Exception as e:
            logger.error(f"加载模型失败: {str(e)}")
            return False

    def close(self):
        """
        关闭数据库连接（使用连接池时无需手动关闭）
        """
        # 连接池会自动管理连接，无需手动关闭
        pass


def main():
    """
    测试深度学习推荐系统
    """
    print("=== 深度学习推荐系统测试 ===")

    # 检查PyTorch是否可用
    if not TORCH_AVAILABLE:
        logger.warning("[FAIL] PyTorch未安装，请安装: pip install torch")
        print("将使用传统推荐算法")
        return

    # 创建推荐引擎
    recommender = DeepLearningRecommendationEngine()

    # 训练模型
    print("\n1. 训练深度学习模型...")
    success = recommender.train_model(epochs=50, batch_size=16)

    if success:
        # 测试推荐
        print("\n2. 测试推荐功能...")
        recommendations = recommender.get_deep_learning_recommendations(1, limit=5)

        logger.info(f"为用户1推荐了 {len(recommendations)} 个单词:")
        for i, rec in enumerate(recommendations):
            print(
                f"  {i+1}. {rec['word']} - {rec['translation']} (分数: {rec['recommendation_score']:.3f})"
            )

        # 保存模型
        print("\n3. 保存模型...")
        recommender.save_model("models/deep_learning_recommender.pth")

    recommender.close()


if __name__ == "__main__":
    main()
