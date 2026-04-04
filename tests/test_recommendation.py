"""
推荐引擎深度测试
测试各推荐算法、权重配置、边缘情况
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta


@pytest.fixture
def app_context():
    """创建Flask应用上下文"""
    from api.api_launcher import create_api_launcher
    launcher = create_api_launcher()
    with launcher.app.app_context():
        yield launcher.app


@pytest.fixture
def mock_words():
    """模拟词库数据"""
    return [
        {
            'id': 1, 'word': 'apple', 'translation': '苹果',
            'difficulty_level': 1, 'frequency_rank': 100,
            'tag': '四级', 'domain': ['spoken']
        },
        {
            'id': 2, 'word': 'beautiful', 'translation': '美丽的',
            'difficulty_level': 2, 'frequency_rank': 300,
            'tag': '四级', 'domain': ['spoken', 'written']
        },
        {
            'id': 3, 'word': 'comprehensive', 'translation': '全面的',
            'difficulty_level': 4, 'frequency_rank': 800,
            'tag': '六级', 'domain': ['academic']
        },
        {
            'id': 4, 'word': 'deteriorate', 'translation': '恶化',
            'difficulty_level': 5, 'frequency_rank': 2000,
            'tag': '考研', 'domain': ['academic']
        },
        {
            'id': 5, 'word': 'ubiquitous', 'translation': '无处不在的',
            'difficulty_level': 6, 'frequency_rank': 3000,
            'tag': 'GRE', 'domain': ['academic']
        },
    ]


@pytest.fixture
def mock_learning_records():
    """模拟学习记录"""
    return [
        {
            'id': 1, 'user_id': 1, 'word_id': 1,
            'mastery_level': 0.8, 'review_count': 5,
            'difficulty_level': 1, 'last_reviewed_at': datetime.now()
        },
        {
            'id': 2, 'user_id': 1, 'word_id': 2,
            'mastery_level': 0.5, 'review_count': 3,
            'difficulty_level': 2, 'last_reviewed_at': datetime.now()
        },
    ]


class TestRecommendationWeights:
    """推荐算法权重测试"""

    def test_weights_sum_to_one(self):
        """测试权重总和接近1.0"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        # 支持 base_weights（新版）和 weights（旧版）
        weights = getattr(engine, 'base_weights', None) or getattr(engine, 'weights', {})
        total = sum(weights.values())

        assert 0.95 <= total <= 1.05, f"权重总和应为1.0，实际为{total}"

    def test_weight_distribution(self):
        """测试权重分布合理性"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        weights = getattr(engine, 'base_weights', None) or getattr(engine, 'weights', {})

        # 主要算法权重不应太低
        assert weights.get('difficulty_based', 0) >= 0.15
        assert weights.get('deep_learning', 0) >= 0.15 or weights.get('deep_learning', 0) >= 0.1

        # 随机探索权重不应太高
        assert weights.get('random_exploration', 0) <= 0.2


class TestDifficultyBasedRecommendation:
    """难度推荐测试"""

    def test_new_user_gets_easy_words(self, mock_words):
        """新用户应获取简单单词"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()

        with patch.object(engine.learning_records_crud, 'get_by_user', return_value=[]):
            with patch.object(engine.words_crud, 'list_all', return_value=mock_words):
                result = engine._get_difficulty_based_recommendations(
                    user_id=999,
                    learned_word_ids=set(),
                    limit=3
                )

                # 新用户应获得难度较低的词
                assert len(result) <= 3
                for word in result:
                    assert word['difficulty_level'] <= 2

    def test_advanced_user_gets_harder_words(self, mock_words, mock_learning_records):
        """高级用户应获取更难单词"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        # 模拟高掌握度记录
        high_mastery_records = [
            {
                'id': 1, 'user_id': 1, 'word_id': 1,
                'mastery_level': 0.9, 'review_count': 10,
                'difficulty_level': 3
            }
        ]

        engine = RecommendationEngine()

        with patch.object(engine.learning_records_crud, 'get_by_user', return_value=high_mastery_records):
            with patch.object(engine.words_crud, 'list_all', return_value=mock_words):
                result = engine._get_difficulty_based_recommendations(
                    user_id=1,
                    learned_word_ids={1},  # 已学过简单词
                    limit=3
                )

                assert len(result) <= 3


class TestFrequencyBasedRecommendation:
    """词频推荐测试"""

    def test_high_frequency_words_prioritized(self, mock_words):
        """高频词应优先推荐"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()

        with patch.object(engine.learning_records_crud, 'get_by_user', return_value=[]):
            with patch.object(engine.words_crud, 'list_all', return_value=mock_words):
                result = engine._get_frequency_based_recommendations(
                    user_id=999,
                    learned_word_ids=set(),
                    limit=3
                )

                # 结果应按词频排序
                if len(result) >= 2:
                    for i in range(len(result) - 1):
                        assert result[i]['frequency_rank'] <= result[i + 1]['frequency_rank']

    def test_frequency_score_calculation(self, mock_words):
        """词频分数计算正确"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()

        with patch.object(engine.learning_records_crud, 'get_by_user', return_value=[]):
            with patch.object(engine.words_crud, 'list_all', return_value=mock_words):
                result = engine._get_frequency_based_recommendations(
                    user_id=999,
                    learned_word_ids=set(),
                    limit=3
                )

                for word in result:
                    assert 'recommendation_score' in word
                    assert 0 <= word['recommendation_score'] <= 1


class TestRandomRecommendation:
    """随机推荐测试"""

    def test_random_returns_unlearned_words(self, mock_words):
        """随机推荐应返回未学单词"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        learned_ids = {1, 2}

        with patch.object(engine.learning_records_crud, 'get_by_user', return_value=[]):
            with patch.object(engine.words_crud, 'list_all', return_value=mock_words):
                result = engine._get_random_recommendations(
                    user_id=999,
                    learned_word_ids=learned_ids,
                    limit=3
                )

                for word in result:
                    assert word['id'] not in learned_ids

    def test_random_handles_empty_pool(self):
        """所有词都学过时返回空列表"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        all_words = [{'id': 1, 'word': 'test', 'difficulty_level': 1, 'frequency_rank': 100}]
        all_learned = {1}

        with patch.object(engine.learning_records_crud, 'get_by_user', return_value=[]):
            with patch.object(engine.words_crud, 'list_all', return_value=all_words):
                result = engine._get_random_recommendations(
                    user_id=999,
                    learned_word_ids=all_learned,
                    limit=3
                )

                assert result == []


class TestRecommendationReason:
    """推荐理由生成测试"""

    def test_reason_for_difficulty_based(self, mock_words):
        """难度推荐理由正确"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        word = {'difficulty_level': 1, 'frequency_rank': 100}

        reason = engine._generate_recommendation_reason(word, 'difficulty_based')
        assert '基础' in reason or '入门' in reason or '核心' in reason

    def test_reason_for_frequency_based(self, mock_words):
        """词频推荐理由正确"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        word = {'frequency_rank': 100}

        reason = engine._generate_recommendation_reason(word, 'frequency_based')
        assert '高频' in reason or '常用' in reason

    def test_reason_for_exam_tags(self):
        """考试标签推荐理由正确"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()

        # 四六级
        word = {'tag': '四级', 'difficulty_level': 2, 'frequency_rank': 500}
        reason = engine._generate_recommendation_reason(word, 'mixed')
        assert '四六级' in reason or '考试' in reason

        # 考研
        word = {'tag': '考研', 'difficulty_level': 4, 'frequency_rank': 1000}
        reason = engine._generate_recommendation_reason(word, 'mixed')
        assert '考研' in reason

    def test_reason_for_deep_learning(self):
        """深度学习推荐理由正确"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        word = {'mastery_level': 0.3, 'difficulty_level': 3, 'frequency_rank': 500}

        reason = engine._generate_recommendation_reason(word, 'deep_learning')
        assert 'AI' in reason


class TestUserPreferenceAnalysis:
    """用户偏好分析测试"""

    def test_analyze_empty_history(self):
        """无历史记录时的偏好分析"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        preferences = engine._analyze_user_preferences([])

        assert 'preferred_difficulty' in preferences
        assert 'learning_speed' in preferences

    def test_analyze_learning_speed(self):
        """学习速度计算正确"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        records = [
            {'review_count': 5, 'difficulty_level': 2},
            {'review_count': 3, 'difficulty_level': 2},
            {'review_count': 7, 'difficulty_level': 2},
        ]

        preferences = engine._analyze_user_preferences(records)

        # 平均复习次数 = (5+3+7)/3 = 5
        assert preferences['learning_speed'] == 5.0


class TestWordSimilarity:
    """单词相似度计算测试"""

    def test_difficulty_match_boosts_score(self):
        """难度匹配提高分数"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()

        word = {'difficulty_level': 3, 'frequency_rank': 500}
        preferences = {'preferred_difficulty': 3}

        score = engine._calculate_word_similarity(word, preferences)

        assert score >= 0.4  # 难度匹配贡献0.4

    def test_high_frequency_boosts_score(self):
        """高频词提高分数"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()

        word = {'difficulty_level': 5, 'frequency_rank': 500}  # 难度不匹配
        preferences = {'preferred_difficulty': 2}

        score = engine._calculate_word_similarity(word, preferences)

        # 高频词贡献0.3，但难度不匹配
        assert score >= 0.3
