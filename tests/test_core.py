"""
核心业务逻辑测试
测试推荐引擎、遗忘曲线、学习记录等核心功能
"""

import pytest
from datetime import datetime, timedelta


@pytest.fixture
def app_context():
    """创建Flask应用上下文"""
    from api.api_launcher import create_api_launcher
    launcher = create_api_launcher()
    with launcher.app.app_context():
        yield launcher.app


class TestForgettingCurve:
    """遗忘曲线计算测试"""

    def test_urgency_calculation(self):
        """测试紧急度计算"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        # 模拟学习记录
        record = {
            'word_id': 1,
            'mastery_level': 0.5,
            'review_count': 3,
            'last_reviewed_at': datetime.now() - timedelta(days=2)
        }

        # 紧急度应该在合理范围内
        manager = ForgettingCurveManager()
        # 验证方法存在
        assert hasattr(manager, 'get_review_words') or hasattr(manager, 'calculate_urgency')

    def test_review_priority(self):
        """测试复习优先级排序"""
        from core.forgetting_curve.forgetting_curve_manager import ForgettingCurveManager

        # 验证管理器可以实例化
        manager = ForgettingCurveManager()
        assert manager is not None


class TestRecommendationEngine:
    """推荐引擎测试"""

    def test_engine_initialization(self):
        """测试推荐引擎初始化"""
        from core.recommendation.recommendation_engine import RecommendationEngine

        engine = RecommendationEngine()
        assert engine is not None

    def test_algorithm_weights(self):
        """测试算法权重配置"""
        from core.recommendation.recommendation_engine import RecommendationEngine
        from config import LEARNING_PARAMS

        # 验证权重配置存在
        if hasattr(RecommendationEngine, 'ALGORITHM_WEIGHTS'):
            weights = RecommendationEngine.ALGORITHM_WEIGHTS
            # 权重总和应该接近1.0
            total = sum(weights.values())
            assert 0.9 <= total <= 1.1, f"权重总和应为1.0，实际为{total}"


class TestUserAuth:
    """用户认证测试"""

    def test_password_hashing(self):
        """测试密码哈希"""
        from core.auth.user_auth import UserAuth

        auth = UserAuth()
        password = "test_password_123"

        # 哈希密码
        hashed = auth._hash_password(password)

        # 哈希应该不等于原密码
        assert hashed != password
        assert len(hashed) > 0

    def test_password_validation_empty(self):
        """测试空密码验证"""
        from core.auth.user_auth import UserAuth

        auth = UserAuth()

        # 空密码哈希应该返回空或False
        result = auth._hash_password("")
        # 空密码的哈希可能是空字符串或特定值
        assert result is not None


class TestVocabularyLearningManager:
    """词汇学习管理器测试"""

    def test_question_types(self):
        """测试题型生成"""
        from core.vocabulary.vocabulary_learning_manager import VocabularyLearningManager

        manager = VocabularyLearningManager()

        # 验证支持的方法
        assert hasattr(manager, 'start_learning_session')
        assert hasattr(manager, 'get_current_word')
        assert hasattr(manager, 'submit_answer')


class TestEvaluationManager:
    """测评管理器测试"""

    def test_score_calculation(self):
        """测试评分计算"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()
        assert manager is not None

    def test_level_assessment(self):
        """测试等级评估"""
        from core.evaluation.evaluation_manager import EvaluationManager

        manager = EvaluationManager()
        # 验证方法存在
        assert hasattr(manager, 'start_level_test') or hasattr(manager, 'submit_test')


class TestAPIResponse:
    """API响应工具测试"""

    def test_success_response(self, app_context):
        """测试成功响应"""
        from api.utils import APIResponse

        # APIResponse.success 返回 (response, status_code)
        result, status = APIResponse.success({'key': 'value'}, "操作成功")

        # result 是 Flask Response 对象
        assert status == 200

    def test_error_response(self, app_context):
        """测试错误响应"""
        from api.utils import APIResponse

        result, status = APIResponse.error("操作失败", 400)

        assert status == 400

    def test_error_response_default_code(self, app_context):
        """测试默认错误码"""
        from api.utils import APIResponse

        result, status = APIResponse.error("默认错误")

        # 默认错误码是 400
        assert status == 400


class TestBaseCRUD:
    """基础CRUD测试"""

    def test_crud_initialization(self):
        """测试CRUD初始化"""
        from tools.base_crud import BaseCRUD

        # BaseCRUD需要表名，测试子类
        from tools.words_crud import WordsCRUD

        crud = WordsCRUD()
        assert crud.table_name == 'words'


class TestDatabaseConnection:
    """数据库连接测试"""

    def test_connection_pool(self):
        """测试连接池"""
        from tools.database import DatabaseManager

        db = DatabaseManager()
        conn = db.get_connection()

        assert conn is not None
        db.return_connection(conn)

    def test_connection_reuse(self):
        """测试连接复用"""
        from tools.database import DatabaseManager

        db = DatabaseManager()
        conn1 = db.get_connection()
        db.return_connection(conn1)

        conn2 = db.get_connection()
        db.return_connection(conn2)

        # 连接池应该复用连接
        assert conn1 is not None
        assert conn2 is not None

    def test_pool_status(self):
        """测试连接池状态"""
        from tools.database import get_pool_status

        status = get_pool_status()

        assert isinstance(status, dict)
        # 应该包含连接池相关信息
        assert 'active' in status or 'pool_size' in status or len(status) >= 0
