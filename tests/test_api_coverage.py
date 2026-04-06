"""
健康检查 API 测试
"""

import pytest


@pytest.fixture
def client():
    """创建测试客户端"""
    from api.api_launcher import create_api_launcher

    launcher = create_api_launcher()
    launcher.app.config["TESTING"] = True
    return launcher.app.test_client()


class TestHealthAPI:
    """健康检查 API 测试"""

    def test_health_check(self, client):
        """测试基础健康检查"""
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["data"]["status"] == "ok"

    def test_health_db_check(self, client):
        """测试数据库健康检查"""
        response = client.get("/api/health/db")
        # 可能成功或失败（取决于数据库连接）
        assert response.status_code in [200, 503]
        data = response.get_json()
        assert "success" in data

    def test_health_cache_check(self, client):
        """测试缓存健康检查"""
        response = client.get("/api/health/cache")
        assert response.status_code in [200, 503]
        data = response.get_json()
        if data["success"]:
            assert "caches" in data["data"]
            assert "summary" in data["data"]

    def test_health_metrics(self, client):
        """测试系统指标"""
        response = client.get("/api/health/metrics")
        assert response.status_code == 200
        data = response.get_json()
        if data["success"]:
            assert "database" in data["data"]
            assert "cache" in data["data"]
            assert "system" in data["data"]


class TestPlansAPI:
    """学习计划 API 测试"""

    def test_get_plans_unauthorized(self, client):
        """测试未授权获取计划列表"""
        response = client.get("/api/plans/1")
        assert response.status_code == 401

    def test_get_active_plan_unauthorized(self, client):
        """测试未授权获取生效计划"""
        response = client.get("/api/plans/1/active")
        assert response.status_code == 401

    def test_create_plan_unauthorized(self, client):
        """测试未授权创建计划"""
        response = client.post(
            "/api/plans",
            json={"user_id": 1, "dataset_type": "cet4"}
        )
        assert response.status_code == 401

    def test_update_plan_unauthorized(self, client):
        """测试未授权更新计划"""
        response = client.put(
            "/api/plans/1",
            json={"daily_new_count": 20}
        )
        assert response.status_code == 401

    def test_delete_plan_unauthorized(self, client):
        """测试未授权删除计划"""
        response = client.delete("/api/plans/1")
        assert response.status_code == 401


class TestLevelsAPI:
    """闯关模式 API 测试"""

    def test_get_gates_public(self, client):
        """测试公开获取关卡列表"""
        response = client.get("/api/levels/gates")
        assert response.status_code == 200

    def test_get_progress_unauthorized(self, client):
        """测试未授权获取进度"""
        response = client.get("/api/levels/progress/1")
        assert response.status_code == 401

    def test_unlock_gate_unauthorized(self, client):
        """测试未授权解锁关卡"""
        response = client.post(
            "/api/levels/unlock",
            json={"user_id": 1, "gate_id": 1}
        )
        assert response.status_code == 401

    def test_complete_gate_unauthorized(self, client):
        """测试未授权完成关卡"""
        response = client.post(
            "/api/levels/complete/1",
            json={"user_id": 1}
        )
        assert response.status_code == 401


class TestEvaluationAPI:
    """评测 API 测试"""

    def test_start_evaluation_unauthorized(self, client):
        """测试未授权开始评测"""
        response = client.post(
            "/api/evaluation/start",
            json={"user_id": 1, "question_count": 10}
        )
        assert response.status_code == 401

    def test_submit_evaluation_unauthorized(self, client):
        """测试未授权提交评测"""
        response = client.post(
            "/api/evaluation/submit",
            json={"user_id": 1, "paper_id": 1, "answers": []}
        )
        assert response.status_code == 401


class TestLearningAPI:
    """学习记录 API 测试"""

    def test_get_progress_unauthorized(self, client):
        """测试未授权获取进度"""
        response = client.get("/api/learning/progress/1")
        assert response.status_code == 401

    def test_get_statistics_unauthorized(self, client):
        """测试未授权获取统计"""
        response = client.get("/api/learning/statistics/1")
        assert response.status_code == 401

    def test_get_records_unauthorized(self, client):
        """测试未授权获取记录"""
        response = client.get("/api/learning/records/1")
        assert response.status_code == 401

    def test_get_forgetting_curve_unauthorized(self, client):
        """测试未授权获取遗忘曲线"""
        response = client.get("/api/learning/forgetting-curve/1")
        assert response.status_code == 401


class TestRecommendationsAPI:
    """推荐 API 测试"""

    def test_get_recommendations_unauthorized(self, client):
        """测试未授权获取推荐"""
        response = client.get("/api/recommendations/1")
        assert response.status_code == 401


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


class TestVocabularyManagement:
    """词汇管理 API 测试"""

    def test_create_word_unauthorized(self, client):
        """测试未授权创建词汇"""
        response = client.post(
            "/api/vocabulary/words",
            json={"word": "test", "translation": "测试"}
        )
        assert response.status_code == 401

    def test_update_word_unauthorized(self, client):
        """测试未授权更新词汇"""
        response = client.put(
            "/api/vocabulary/words/1",
            json={"word": "test2"}
        )
        assert response.status_code == 401

    def test_delete_word_unauthorized(self, client):
        """测试未授权删除词汇"""
        response = client.delete("/api/vocabulary/words/1")
        assert response.status_code == 401

    def test_import_words_unauthorized(self, client):
        """测试未授权导入词汇"""
        response = client.post("/api/vocabulary/import", json={"words": []})
        assert response.status_code == 401

    def test_export_words_unauthorized(self, client):
        """测试未授权导出词汇"""
        response = client.get("/api/vocabulary/export")
        assert response.status_code == 401


class TestAchievementsAPI:
    """成就 API 测试"""

    def test_get_achievements_unauthorized(self, client):
        """测试未授权获取成就"""
        response = client.get("/api/achievements/1")
        assert response.status_code == 401

    def test_get_streak_unauthorized(self, client):
        """测试未授权获取连续学习天数"""
        response = client.get("/api/achievements/1/streak")
        assert response.status_code == 401

    def test_update_streak_unauthorized(self, client):
        """测试未授权更新连续学习"""
        response = client.post("/api/achievements/1/streak/update")
        assert response.status_code == 401

    def test_get_reports_unauthorized(self, client):
        """测试未授权获取学习报告"""
        response = client.get("/api/achievements/1/reports")
        assert response.status_code == 401

    def test_get_weekly_report_unauthorized(self, client):
        """测试未授权获取周报"""
        response = client.get("/api/achievements/1/reports/weekly")
        assert response.status_code == 401


class TestLearningAPIExtended:
    """学习 API 扩展测试"""

    def test_get_record_unauthorized(self, client):
        """测试未授权获取单条记录"""
        response = client.get("/api/learning/record/1")
        assert response.status_code == 401

    def test_update_record_unauthorized(self, client):
        """测试未授权更新记录"""
        response = client.put("/api/learning/record/1", json={"mastery_level": 0.5})
        assert response.status_code == 401

    def test_delete_record_unauthorized(self, client):
        """测试未授权删除记录"""
        response = client.delete("/api/learning/record/1")
        assert response.status_code == 401

    def test_get_sessions_unauthorized(self, client):
        """测试未授权获取会话列表"""
        response = client.get("/api/learning/sessions/1")
        assert response.status_code == 401

    def test_delete_session_unauthorized(self, client):
        """测试未授权删除会话"""
        response = client.delete("/api/learning/session/1")
        assert response.status_code == 401
