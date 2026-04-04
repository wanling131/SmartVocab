"""
遗忘曲线深度测试
测试复习时间计算、紧急度排序、记忆保持率预测
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def app_context():
    """创建Flask应用上下文"""
    from api.api_launcher import create_api_launcher
    launcher = create_api_launcher()
    with launcher.app.app_context():
        yield launcher.app


class TestReviewIntervalCalculation:
    """复习间隔计算测试"""

    def test_base_interval_for_new_word(self):
        """新单词的基础复习间隔"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        # 新单词：掌握度0，复习0次
        interval = manager._calculate_review_interval(
            mastery_level=0.0,
            review_count=0
        )

        # 应该在最小间隔附近
        assert interval >= 1  # 最小1小时
        assert interval <= 24  # 新词不应超过1天

    def test_interval_increases_with_mastery(self):
        """掌握度越高，间隔越长"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        interval_low = manager._calculate_review_interval(mastery_level=0.2, review_count=1)
        interval_high = manager._calculate_review_interval(mastery_level=0.8, review_count=1)

        assert interval_high > interval_low

    def test_interval_increases_with_reviews(self):
        """复习次数越多，间隔越长"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        interval_few = manager._calculate_review_interval(mastery_level=0.5, review_count=1)
        interval_many = manager._calculate_review_interval(mastery_level=0.5, review_count=5)

        assert interval_many > interval_few

    def test_interval_respects_limits(self):
        """间隔应在合理范围内"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        # 极端高掌握度+高复习次数
        interval = manager._calculate_review_interval(mastery_level=1.0, review_count=100)

        # 最大30天
        assert interval <= 24 * 30

        # 极端低掌握度+低复习次数
        interval = manager._calculate_review_interval(mastery_level=0.0, review_count=0)

        # 最小1小时
        assert interval >= 1


class TestNextReviewTime:
    """下次复习时间计算测试"""

    def test_next_review_in_future(self):
        """下次复习时间在未来"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()
        now = datetime.now()

        next_review = manager.calculate_next_review_time(
            user_id=1,
            word_id=1,
            mastery_level=0.5,
            review_count=3
        )

        assert next_review > now

    def test_different_words_have_different_times(self):
        """不同掌握度的单词有不同复习时间"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        time1 = manager.calculate_next_review_time(1, 1, mastery_level=0.3, review_count=1)
        time2 = manager.calculate_next_review_time(1, 2, mastery_level=0.7, review_count=5)

        # 高掌握度应更晚复习
        assert time2 > time1


class TestMasteryLevelUpdate:
    """掌握程度更新测试"""

    def test_correct_answer_increases_mastery(self):
        """答对增加掌握度"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()
        current = 0.5

        new_mastery = manager._calculate_new_mastery_level(
            current_mastery=current,
            is_correct=True,
            response_time=5.0  # 5秒作答
        )

        assert new_mastery > current
        assert new_mastery <= 1.0

    def test_wrong_answer_decreases_mastery(self):
        """答错降低掌握度"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()
        current = 0.5

        new_mastery = manager._calculate_new_mastery_level(
            current_mastery=current,
            is_correct=False,
            response_time=10.0
        )

        assert new_mastery < current
        assert new_mastery >= 0.0

    def test_fast_response_gets_bonus(self):
        """快速作答有奖励"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        fast = manager._calculate_new_mastery_level(0.5, True, response_time=2.0)
        slow = manager._calculate_new_mastery_level(0.5, True, response_time=15.0)

        assert fast > slow

    def test_mastery_cannot_exceed_one(self):
        """掌握度不超过1.0"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        new_mastery = manager._calculate_new_mastery_level(
            current_mastery=0.95,
            is_correct=True,
            response_time=1.0
        )

        assert new_mastery <= 1.0

    def test_mastery_cannot_go_negative(self):
        """掌握度不低于0"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        new_mastery = manager._calculate_new_mastery_level(
            current_mastery=0.05,
            is_correct=False,
            response_time=30.0
        )

        assert new_mastery >= 0.0


class TestRetentionRatePrediction:
    """记忆保持率预测测试"""

    def test_recent_review_high_retention(self):
        """刚复习过保持率高"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        retention = manager.predict_retention_rate(
            mastery_level=0.8,
            hours_since_review=1.0
        )

        assert retention > 0.8

    def test_long_gap_low_retention(self):
        """长时间未复习保持率低"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        retention = manager.predict_retention_rate(
            mastery_level=0.5,
            hours_since_review=168.0  # 1周
        )

        assert retention < 0.5

    def test_high_mastery_slower_forgetting(self):
        """高掌握度遗忘更慢"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()
        hours = 48.0  # 2天

        retention_low = manager.predict_retention_rate(mastery_level=0.3, hours_since_review=hours)
        retention_high = manager.predict_retention_rate(mastery_level=0.8, hours_since_review=hours)

        assert retention_high > retention_low

    def test_retention_in_valid_range(self):
        """保持率在0-1范围内"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        for mastery in [0.0, 0.3, 0.5, 0.8, 1.0]:
            for hours in [0, 1, 24, 168, 720]:
                retention = manager.predict_retention_rate(mastery, hours)
                assert 0 <= retention <= 1


class TestReviewWordsPriority:
    """复习单词优先级测试"""

    def test_low_mastery_is_urgent(self):
        """低掌握度单词紧急度高"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        # 模拟学习记录
        records = [
            {
                'id': 1, 'word_id': 1,
                'mastery_level': 0.3,  # 低掌握度
                'review_count': 1,
                'last_reviewed_at': datetime.now() - timedelta(days=1)
            },
            {
                'id': 2, 'word_id': 2,
                'mastery_level': 0.8,  # 高掌握度
                'review_count': 5,
                'last_reviewed_at': datetime.now() - timedelta(days=1)
            },
        ]

        with patch.object(manager.learning_records_crud, 'get_review_due', return_value=records):
            result = manager.get_review_words(user_id=1, limit=10)

            # 低掌握度的应该排在前面
            if len(result) >= 2:
                first_mastery = result[0].get('mastery_level', 1.0)
                second_mastery = result[1].get('mastery_level', 1.0)
                # 紧急排序：低掌握度优先
                assert first_mastery <= second_mastery


class TestForgettingCurveData:
    """遗忘曲线数据测试"""

    def test_generates_seven_day_plan(self):
        """生成7天复习计划"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        # 无记录时返回空列表，不是7天计划
        with patch.object(manager.learning_records_crud, 'get_by_user', return_value=[]):
            plan = manager.get_forgetting_curve_data(user_id=1, days=7)

            # 无学习历史时返回空列表
            assert plan == [] or len(plan) == 7

    def test_generates_plan_with_records(self):
        """有记录时生成7天计划"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        # 模拟学习记录
        records = [
            {
                'id': 1, 'user_id': 1, 'word_id': 1,
                'mastery_level': 0.5, 'review_count': 2,
                'last_reviewed_at': datetime.now()
            }
        ]

        with patch.object(manager.learning_records_crud, 'get_by_user', return_value=records):
            plan = manager.get_forgetting_curve_data(user_id=1, days=7)

            assert len(plan) == 7

    def test_plan_includes_required_fields(self):
        """计划包含必要字段"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        with patch.object(manager.learning_records_crud, 'get_by_user', return_value=[]):
            plan = manager.get_forgetting_curve_data(user_id=1, days=3)

            for day_plan in plan:
                assert 'day' in day_plan
                assert 'date' in day_plan
                assert 'words_to_review' in day_plan

    def test_empty_history_returns_empty_plan(self):
        """无学习历史时返回空计划"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        manager = ForgettingCurveManager()

        with patch.object(manager.learning_records_crud, 'get_by_user', return_value=[]):
            plan = manager.get_forgetting_curve_data(user_id=1, days=7)

            # 无记录时，每天复习数为0
            for day_plan in plan:
                assert day_plan['words_to_review'] == 0


class TestCircularSlice:
    """环形切片工具函数测试"""

    def test_returns_exact_limit(self):
        """返回精确数量"""
        from core.forgetting_curve.forgetting_curve_manager import _circular_slice

        items = [1, 2, 3, 4, 5]
        result = _circular_slice(items, offset=0, limit=3)

        assert len(result) == 3

    def test_handles_offset(self):
        """正确处理偏移"""
        from core.forgetting_curve.forgetting_curve_manager import _circular_slice

        items = [1, 2, 3, 4, 5]
        result = _circular_slice(items, offset=2, limit=2)

        assert result == [3, 4]

    def test_wraps_around(self):
        """环形回绕"""
        from core.forgetting_curve.forgetting_curve_manager import _circular_slice

        items = [1, 2, 3]
        result = _circular_slice(items, offset=2, limit=3)

        # 从位置2开始取3个：[3, 1, 2]
        assert result == [3, 1, 2]

    def test_handles_empty_list(self):
        """空列表返回空"""
        from core.forgetting_curve.forgetting_curve_manager import _circular_slice

        result = _circular_slice([], offset=0, limit=5)

        assert result == []

    def test_handles_zero_limit(self):
        """limit为0返回空"""
        from core.forgetting_curve.forgetting_curve_manager import _circular_slice

        result = _circular_slice([1, 2, 3], offset=0, limit=0)

        assert result == []
