"""学习记录API测试"""

import pytest


@pytest.fixture
def client():
    """创建测试客户端"""
    from api.api_launcher import create_api_launcher
    launcher = create_api_launcher()
    launcher.app.config["TESTING"] = True
    return launcher.app.test_client()


class TestLearningAPI:
    """学习相关API测试"""

    def test_get_progress_unauthorized(self, client):
        """测试未授权获取进度"""
        r = client.get("/api/learning/progress/1")
        assert r.status_code == 401

    def test_get_statistics_unauthorized(self, client):
        """测试未授权获取统计"""
        r = client.get("/api/learning/statistics/1")
        assert r.status_code == 401

    def test_get_records_unauthorized(self, client):
        """测试未授权获取记录"""
        r = client.get("/api/learning/records/1")
        assert r.status_code == 401

    def test_get_forgetting_curve_unauthorized(self, client):
        """测试未授权获取遗忘曲线"""
        r = client.get("/api/learning/forgetting-curve/1")
        assert r.status_code == 401


class TestPlansAPI:
    """学习计划API测试"""

    def test_get_plans_unauthorized(self, client):
        """测试未授权获取计划列表"""
        r = client.get("/api/plans/1")
        assert r.status_code == 401

    def test_get_active_plan_unauthorized(self, client):
        """测试未授权获取生效计划"""
        r = client.get("/api/plans/1/active")
        assert r.status_code == 401

    def test_create_plan_unauthorized(self, client):
        """测试未授权创建计划"""
        r = client.post("/api/plans", json={"user_id": 1, "dataset_type": "cet4"})
        assert r.status_code == 401

    def test_start_plan_learning_unauthorized(self, client):
        """测试未授权开始计划学习"""
        r = client.post("/api/plans/1/start-learning")
        assert r.status_code == 401


class TestVocabularyAPI:
    """词汇API测试"""

    def test_start_session_unauthorized(self, client):
        """测试未授权开始学习会话"""
        r = client.post("/api/vocabulary/start-session",
                       json={"user_id": 1, "difficulty_level": 2, "word_count": 10})
        assert r.status_code == 401

    def test_start_review_unauthorized(self, client):
        """测试未授权开始复习"""
        r = client.post("/api/vocabulary/start-review-session",
                       json={"user_id": 1})
        assert r.status_code == 401

    def test_import_words_unauthorized(self, client):
        """测试未授权导入词库"""
        r = client.post("/api/vocabulary/import", json=[])
        assert r.status_code == 401

    def test_export_words_unauthorized(self, client):
        """测试未授权导出词库"""
        r = client.get("/api/vocabulary/export")
        assert r.status_code == 401


class TestLevelsAPI:
    """闯关模式API测试"""

    def test_get_gates_public(self, client):
        """测试获取关卡列表（公开）"""
        r = client.get("/api/levels/gates")
        # 不应该返回401
        assert r.status_code != 401

    def test_get_progress_unauthorized(self, client):
        """测试未授权获取进度"""
        r = client.get("/api/levels/progress/1")
        assert r.status_code == 401

    def test_start_gate_unauthorized(self, client):
        """测试未授权开始闯关"""
        r = client.post("/api/levels/start/1", json={"user_id": 1})
        assert r.status_code == 401


class TestEvaluationAPI:
    """评测API测试"""

    def test_start_evaluation_unauthorized(self, client):
        """测试未授权开始评测"""
        r = client.post("/api/evaluation/start",
                       json={"user_id": 1, "question_count": 10})
        assert r.status_code == 401

    def test_submit_evaluation_unauthorized(self, client):
        """测试未授权提交评测"""
        r = client.post("/api/evaluation/submit",
                       json={"user_id": 1, "paper_id": 1, "answers": []})
        assert r.status_code == 401


class TestRecommendationsAPI:
    """推荐API测试"""

    def test_get_recommendations_unauthorized(self, client):
        """测试未授权获取推荐"""
        r = client.get("/api/recommendations/1")
        assert r.status_code == 401
