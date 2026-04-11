"""认证模块测试"""

import pytest
import os


@pytest.fixture
def client():
    """创建测试客户端"""
    from api.api_launcher import create_api_launcher

    launcher = create_api_launcher()
    launcher.app.config["TESTING"] = True
    return launcher.app.test_client()


class TestJWTToken:
    """JWT Token 相关测试"""

    def test_generate_token(self):
        """测试 Token 生成"""
        from api.auth_middleware import generate_token

        token = generate_token(user_id=1, username="testuser")
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT token 通常较长

    def test_verify_valid_token(self):
        """测试有效 Token 验证"""
        from api.auth_middleware import generate_token, verify_token

        token = generate_token(user_id=1, username="testuser")
        payload = verify_token(token)

        assert payload is not None
        assert payload.get("user_id") == 1
        assert payload.get("username") == "testuser"

    def test_verify_invalid_token(self):
        """测试无效 Token 验证"""
        from api.auth_middleware import verify_token

        payload = verify_token("invalid.token.here")
        assert payload is None

    def test_verify_empty_token(self):
        """测试空 Token 验证"""
        from api.auth_middleware import verify_token

        payload = verify_token("")
        assert payload is None


class TestRequireAuth:
    """@require_auth 装饰器测试"""

    def test_protected_endpoint_without_token(self, client):
        """测试未携带 Token 访问受保护端点"""
        # /api/auth/verify 需要登录
        r = client.get("/api/auth/verify")
        assert r.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, client):
        """测试携带无效 Token 访问受保护端点"""
        r = client.get(
            "/api/auth/verify",
            headers={"Authorization": "Bearer invalid_token"}
        )
        assert r.status_code == 401

    def test_public_endpoint_without_token(self, client):
        """测试公开端点无需 Token"""
        r = client.get("/api/health")
        assert r.status_code == 200

    def test_levels_gates_public(self, client):
        """测试关卡列表为公开接口"""
        r = client.get("/api/levels/gates")
        # 即使返回错误（如数据库未连接），也不应为 401
        assert r.status_code != 401


class TestUserAccess:
    """用户身份校验测试"""

    def test_check_user_access_with_matching_user(self):
        """测试用户 ID 匹配"""
        from api.auth_middleware import generate_token, verify_token

        token = generate_token(user_id=123, username="alice")
        payload = verify_token(token)

        # 模拟身份校验逻辑
        user_id_in_request = 123
        has_access = payload and payload.get("user_id") == user_id_in_request
        assert has_access is True

    def test_check_user_access_with_different_user(self):
        """测试用户 ID 不匹配"""
        from api.auth_middleware import generate_token, verify_token

        token = generate_token(user_id=123, username="alice")
        payload = verify_token(token)

        # 模拟身份校验逻辑
        user_id_in_request = 456
        has_access = payload and payload.get("user_id") == user_id_in_request
        assert has_access is False


class TestAdminPermission:
    """管理员权限测试"""

    def test_is_admin_when_not_configured(self):
        """测试未配置 ADMIN_USERS 时拒绝所有用户"""
        # 需要在没有 ADMIN_USERS 环境变量的情况下测试
        original = os.environ.get("ADMIN_USERS", "")
        try:
            os.environ.pop("ADMIN_USERS", None)
            # 重新导入以应用新配置
            import importlib
            import tools.admin_utils
            importlib.reload(tools.admin_utils)

            from tools.admin_utils import is_admin
            # 未配置时返回 False（安全默认值）
            assert is_admin() is False
        finally:
            if original:
                os.environ["ADMIN_USERS"] = original

    def test_admin_users_parsing(self):
        """测试管理员用户名列表解析"""
        original = os.environ.get("ADMIN_USERS", "")
        try:
            os.environ["ADMIN_USERS"] = "admin,root,teacher"
            # 重新导入以应用新配置
            import importlib
            import tools.admin_utils
            importlib.reload(tools.admin_utils)

            from tools.admin_utils import ADMIN_USERS
            assert "admin" in ADMIN_USERS
            assert "root" in ADMIN_USERS
            assert "teacher" in ADMIN_USERS
            assert "other" not in ADMIN_USERS
        finally:
            if original:
                os.environ["ADMIN_USERS"] = original
            else:
                os.environ.pop("ADMIN_USERS", None)


class TestAuthAPIEndpoints:
    """认证API端点测试"""

    def test_register_endpoint_exists(self, client):
        """测试注册端点存在"""
        r = client.post("/api/auth/register", json={
            "username": "test_new_user",
            "password": "TestPass123",
            "email": "test@example.com"
        })
        # 可能成功或失败（用户已存在），但不应是404
        assert r.status_code in [200, 201, 400, 409, 500]

    def test_register_missing_fields(self, client):
        """测试注册缺少必填字段"""
        r = client.post("/api/auth/register", json={})
        assert r.status_code in [400, 500]

    def test_password_change_unauthorized(self, client):
        """测试未授权修改密码"""
        r = client.put("/api/auth/password/1", json={
            "old_password": "old",
            "new_password": "new"
        })
        assert r.status_code == 401

    def test_login_endpoint_exists(self, client):
        """测试登录端点存在"""
        r = client.post("/api/auth/login", json={
            "username": "nonexistent_user_xyz",
            "password": "wrong_password"
        })
        # 用户不存在应返回401
        assert r.status_code == 401
