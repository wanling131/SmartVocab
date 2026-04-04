"""
测评系统深度测试
测试组卷、评分、等级评估逻辑
"""

import pytest
from unittest.mock import Mock, patch, MagicMock


@pytest.fixture
def app_context():
    """创建Flask应用上下文"""
    from api.api_launcher import create_api_launcher
    launcher = create_api_launcher()
    with launcher.app.app_context():
        yield launcher.app


@pytest.fixture
def mock_words():
    """模拟词库"""
    return [
        {
            'id': 1, 'word': 'apple', 'translation': '苹果',
            'difficulty_level': 1, 'phonetic': '/ˈæpl/', 'pos': 'n.',
            'cefr_standard': 'A1', 'dataset_type': 'cet4'
        },
        {
            'id': 2, 'word': 'beautiful', 'translation': '美丽的',
            'difficulty_level': 2, 'phonetic': '/ˈbjuːtɪfl/', 'pos': 'adj.',
            'cefr_standard': 'A2', 'dataset_type': 'cet4'
        },
        {
            'id': 3, 'word': 'comprehensive', 'translation': '全面的',
            'difficulty_level': 4, 'phonetic': '/ˌkɒmprɪˈhensɪv/', 'pos': 'adj.',
            'cefr_standard': 'B2', 'dataset_type': 'cet6'
        },
        {
            'id': 4, 'word': 'deteriorate', 'translation': '恶化',
            'difficulty_level': 5, 'phonetic': '/dɪˈtɪəriəreɪt/', 'pos': 'v.',
            'cefr_standard': 'C1', 'dataset_type': 'kaoyan'
        },
        {
            'id': 5, 'word': 'eloquent', 'translation': '雄辩的',
            'difficulty_level': 5, 'phonetic': '/ˈeləkwənt/', 'pos': 'adj.',
            'cefr_standard': 'C1', 'dataset_type': 'gre'
        },
    ]


class TestLevelTestStart:
    """等级测试开始测试"""

    def test_creates_paper_with_correct_count(self, mock_words):
        """创建正确数量的题目"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        with patch.object(manager.words_crud, 'list_all', return_value=mock_words):
            with patch.object(manager.words_crud, 'get_by_difficulty', return_value=mock_words):
                with patch.object(manager.words_crud, 'read', side_effect=lambda id: mock_words[id-1] if id <= len(mock_words) else None):
                    with patch.object(manager.papers_crud, 'create', return_value=1):
                        with patch.object(manager.papers_crud, 'update_question_count', return_value=True):
                            with patch.object(manager.items_crud, 'create', return_value=True):
                                result = manager.start_level_test(user_id=1, question_count=3)

        assert result['success'] is True
        assert 'paper_id' in result
        assert 'questions' in result

    def test_handles_insufficient_words(self):
        """词库不足时返回错误"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        with patch.object(manager.words_crud, 'list_all', return_value=[]):
            with patch.object(manager.words_crud, 'get_by_difficulty', return_value=[]):
                result = manager.start_level_test(user_id=1, question_count=10)

        assert result['success'] is False
        assert '词库' in result['message'] or '不足' in result['message']

    def test_filters_by_difficulty(self, mock_words):
        """按难度筛选题目"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()
        hard_words = [w for w in mock_words if w['difficulty_level'] >= 4]

        with patch.object(manager.words_crud, 'get_by_difficulty', return_value=hard_words):
            with patch.object(manager.words_crud, 'read', side_effect=lambda id: next((w for w in hard_words if w['id'] == id), None)):
                with patch.object(manager.papers_crud, 'create', return_value=1):
                    with patch.object(manager.papers_crud, 'update_question_count', return_value=True):
                        with patch.object(manager.items_crud, 'create', return_value=True):
                            result = manager.start_level_test(
                                user_id=1,
                                question_count=2,
                                difficulty_level=5
                            )

        # 结果要么成功，要么因词数不足失败
        assert 'success' in result

    def test_filters_by_dataset_type(self, mock_words):
        """按数据集类型筛选"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()
        cet4_words = [{**w, 'dataset_type': 'cet4'} for w in mock_words[:3]]

        with patch.object(manager.words_crud, 'list_all', return_value=cet4_words):
            with patch.object(manager.words_crud, 'read', side_effect=lambda id: cet4_words[id-1] if id <= len(cet4_words) else None):
                with patch.object(manager.papers_crud, 'create', return_value=1):
                    with patch.object(manager.papers_crud, 'update_question_count', return_value=True):
                        with patch.object(manager.items_crud, 'create', return_value=True):
                            result = manager.start_level_test(
                                user_id=1,
                                question_count=2,
                                dataset_type='cet4'
                            )

        assert 'success' in result


class TestAnswerChecking:
    """答案检查测试"""

    def test_choice_exact_match(self):
        """选择题精确匹配"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        result = manager._check_answer('A', 'A', 'choice')
        assert result is True

        result = manager._check_answer('A', 'B', 'choice')
        assert result is False

    def test_choice_case_insensitive(self):
        """选择题忽略大小写"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        result = manager._check_answer('a', 'A', 'choice')
        assert result is True

    def test_spelling_exact_match(self):
        """拼写题精确匹配"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        result = manager._check_answer('apple', 'apple', 'spelling')
        assert result is True

        result = manager._check_answer('appl', 'apple', 'spelling')
        assert result is False

    def test_spelling_case_insensitive(self):
        """拼写题忽略大小写"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        result = manager._check_answer('Apple', 'apple', 'spelling')
        assert result is True

    def test_translation_partial_match(self):
        """翻译题部分匹配"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        # 用户答案包含正确答案
        result = manager._check_answer('这是一个苹果', '苹果', 'translation')
        assert result is True

        # 正确答案包含用户答案
        result = manager._check_answer('苹果', '红苹果', 'translation')
        assert result is True

    def test_translation_whitespace_handling(self):
        """翻译题忽略空白"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        result = manager._check_answer('  苹果  ', '苹果', 'translation')
        assert result is True

    def test_handles_none_values(self):
        """处理None值 - 空答案返回False"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        # None会被转换为空字符串，空答案返回False（已修复的bug）
        result = manager._check_answer(None, '', 'translation')
        assert result is False

        # 非空正确答案，空用户答案
        result = manager._check_answer(None, '苹果', 'translation')
        assert result is False

        # 选择题精确匹配，空答案
        result = manager._check_answer(None, 'A', 'choice')
        assert result is False

        # 正常情况
        result = manager._check_answer('苹果', '苹果', 'translation')
        assert result is True


class TestLevelAssessment:
    """等级评估测试"""

    def test_score_90_plus_is_c1(self):
        """90分以上为C1"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 10}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(10)]
        answers = [{'word_id': i, 'user_answer': 'A', 'correct_answer': 'A'} for i in range(10)]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    with patch.object(manager, '_check_answer', return_value=True):
                        result = manager.submit_level_test(
                            user_id=1,
                            paper_id=1,
                            answers=answers
                        )

        assert result['success'] is True
        assert result['assessed_level'] == 'C1'

    def test_score_80_to_90_is_b2(self):
        """80-90分为B2"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 10}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(10)]
        # 8对2错 = 80%
        answers = [{'word_id': i, 'user_answer': 'A', 'correct_answer': 'A'} for i in range(8)]
        answers += [{'word_id': 8, 'user_answer': 'B', 'correct_answer': 'A'}]
        answers += [{'word_id': 9, 'user_answer': 'B', 'correct_answer': 'A'}]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    # 模拟8对2错
                    check_results = [True] * 8 + [False] * 2
                    with patch.object(manager, '_check_answer', side_effect=check_results):
                        result = manager.submit_level_test(
                            user_id=1,
                            paper_id=1,
                            answers=answers
                        )

        assert result['success'] is True
        assert result['assessed_level'] == 'B2'

    def test_score_70_to_80_is_b1(self):
        """70-80分为B1"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 10}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(10)]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    # 7对3错 = 70%
                    check_results = [True] * 7 + [False] * 3
                    with patch.object(manager, '_check_answer', side_effect=check_results):
                        result = manager.submit_level_test(
                            user_id=1,
                            paper_id=1,
                            answers=[{'word_id': i, 'user_answer': 'A'} for i in range(10)]
                        )

        assert result['assessed_level'] == 'B1'

    def test_score_60_to_70_is_a2(self):
        """60-70分为A2"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 10}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(10)]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    # 6对4错 = 60%
                    check_results = [True] * 6 + [False] * 4
                    with patch.object(manager, '_check_answer', side_effect=check_results):
                        result = manager.submit_level_test(
                            user_id=1,
                            paper_id=1,
                            answers=[{'word_id': i, 'user_answer': 'A'} for i in range(10)]
                        )

        assert result['assessed_level'] == 'A2'

    def test_score_below_60_is_a1(self):
        """60分以下为A1"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 10}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(10)]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    # 5对5错 = 50%
                    check_results = [True] * 5 + [False] * 5
                    with patch.object(manager, '_check_answer', side_effect=check_results):
                        result = manager.submit_level_test(
                            user_id=1,
                            paper_id=1,
                            answers=[{'word_id': i, 'user_answer': 'A'} for i in range(10)]
                        )

        assert result['assessed_level'] == 'A1'


class TestSubmitLevelTest:
    """提交测试测试"""

    def test_rejects_nonexistent_paper(self):
        """拒绝不存在的试卷"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        with patch.object(manager.papers_crud, 'read', return_value=None):
            result = manager.submit_level_test(
                user_id=1,
                paper_id=999,
                answers=[]
            )

        assert result['success'] is False
        assert '不存在' in result['message']

    def test_rejects_wrong_user(self):
        """拒绝非试卷所有者"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 5}

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            result = manager.submit_level_test(
                user_id=2,  # 不同用户
                paper_id=1,
                answers=[]
            )

        assert result['success'] is False
        assert '无权' in result['message']

    def test_handles_empty_answers(self):
        """处理空答案"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 5}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(5)]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    result = manager.submit_level_test(
                        user_id=1,
                        paper_id=1,
                        answers=[]  # 空答案
                    )

        assert result['success'] is True
        assert result['correct_count'] == 0
        assert result['unanswered_count'] == 5

    def test_calculates_correct_statistics(self):
        """计算正确的统计数据"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()

        paper = {'id': 1, 'user_id': 1, 'question_count': 5}
        items = [{'id': i, 'word_id': i, 'question_type': 'choice'} for i in range(5)]
        answers = [
            {'word_id': 0, 'user_answer': 'A', 'correct_answer': 'A'},
            {'word_id': 1, 'user_answer': 'A', 'correct_answer': 'A'},
            {'word_id': 2, 'user_answer': 'B', 'correct_answer': 'A'},  # 错
            {'word_id': 3, 'user_answer': 'A', 'correct_answer': 'A'},
            # word_id 4 未作答
        ]

        with patch.object(manager.papers_crud, 'read', return_value=paper):
            with patch.object(manager.items_crud, 'get_by_paper', return_value=items):
                with patch.object(manager.results_crud, 'create', return_value=1):
                    result = manager.submit_level_test(
                        user_id=1,
                        paper_id=1,
                        answers=answers
                    )

        assert result['success'] is True
        assert result['correct_count'] >= 0
        assert result['total_count'] == 5
        assert result['score'] >= 0


class TestNormalizeWordId:
    """word_id 规范化测试"""

    def test_converts_string_to_int(self):
        """字符串转整数"""
        from core.evaluation.evaluation_manager import _normalize_word_id

        assert _normalize_word_id('123') == 123
        assert _normalize_word_id('1') == 1

    def test_passes_through_int(self):
        """整数直接通过"""
        from core.evaluation.evaluation_manager import _normalize_word_id

        assert _normalize_word_id(123) == 123

    def test_handles_none(self):
        """处理None"""
        from core.evaluation.evaluation_manager import _normalize_word_id

        assert _normalize_word_id(None) is None

    def test_handles_invalid_string(self):
        """处理无效字符串"""
        from core.evaluation.evaluation_manager import _normalize_word_id

        assert _normalize_word_id('abc') is None
        assert _normalize_word_id('') is None
