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


class TestAuthMiddleware:
    """认证中间件测试"""

    def test_check_user_access_function(self, client):
        """测试 check_user_access 函数（在请求上下文中）"""
        from api.auth_middleware import check_user_access

        # 在没有登录的情况下，应该返回 False
        # 需要在请求上下文中调用
        with client.application.test_request_context():
            result = check_user_access(1)
            assert result == False

    def test_generate_and_verify_token(self):
        """测试 Token 生成和验证"""
        from api.auth_middleware import generate_token, verify_token

        token = generate_token(user_id=1, username="testuser")
        assert token is not None
        assert isinstance(token, str)

        payload = verify_token(token)
        assert payload is not None
        assert payload.get("user_id") == 1
        assert payload.get("username") == "testuser"

    def test_verify_invalid_token(self):
        """测试验证无效 Token"""
        from api.auth_middleware import verify_token

        result = verify_token("invalid.token.here")
        assert result is None

    def test_verify_empty_token(self):
        """测试验证空 Token"""
        from api.auth_middleware import verify_token

        result = verify_token("")
        assert result is None


class TestLevelsAPI:
    """关卡 API 测试"""

    def test_get_gates_public(self, client):
        """测试公开获取关卡列表"""
        r = client.get("/api/levels/gates")
        assert r.status_code == 200

    def test_unlock_gate_unauthorized(self, client):
        """测试未授权解锁关卡"""
        r = client.post("/api/levels/unlock", json={"user_id": 1, "gate_id": 1})
        assert r.status_code == 401

    def test_complete_gate_unauthorized(self, client):
        """测试未授权完成关卡"""
        r = client.post("/api/levels/complete/1", json={"user_id": 1})
        assert r.status_code == 401


class TestVocabularyManagement:
    """词汇管理 API 测试"""

    def test_create_word_unauthorized(self, client):
        """测试未授权创建词汇"""
        r = client.post("/api/vocabulary/words", json={"word": "test", "translation": "测试"})
        assert r.status_code == 401

    def test_update_word_unauthorized(self, client):
        """测试未授权更新词汇"""
        r = client.put("/api/vocabulary/words/1", json={"word": "test2"})
        assert r.status_code == 401

    def test_delete_word_unauthorized(self, client):
        """测试未授权删除词汇"""
        r = client.delete("/api/vocabulary/words/1")
        assert r.status_code == 401

    def test_import_words_unauthorized(self, client):
        """测试未授权导入词汇"""
        r = client.post("/api/vocabulary/import", json={"words": []})
        assert r.status_code == 401

    def test_export_words_unauthorized(self, client):
        """测试未授权导出词汇"""
        r = client.get("/api/vocabulary/export")
        assert r.status_code == 401


class TestEvaluationResults:
    """评估结果 API 测试"""

    def test_get_result_unauthorized(self, client):
        """测试未授权获取评估结果"""
        r = client.get("/api/evaluation/result/1")
        assert r.status_code == 401

    def test_get_results_list_unauthorized(self, client):
        """测试未授权获取评估历史"""
        r = client.get("/api/evaluation/history/1")
        assert r.status_code == 401
