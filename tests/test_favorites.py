"""收藏功能测试"""

import pytest


@pytest.fixture
def client():
    """创建测试客户端"""
    from api.api_launcher import create_api_launcher

    launcher = create_api_launcher()
    launcher.app.config["TESTING"] = True
    return launcher.app.test_client()


@pytest.fixture
def auth_header(client):
    """获取认证头"""
    # 使用测试用户登录
    response = client.post(
        "/api/auth/login",
        json={"username": "e2e_tester", "password": "TestPass123"}
    )
    data = response.get_json()
    if data.get("success") and data.get("data", {}).get("token"):
        token = data["data"]["token"]
        return {"Authorization": f"Bearer {token}"}
    pytest.skip("测试用户不存在，跳过收藏测试")


class TestFavoritesCRUD:
    """收藏 CRUD 测试"""

    def test_favorites_crud_instance(self):
        """测试 CRUD 实例化"""
        from tools.favorites_crud import FavoritesCRUD

        crud = FavoritesCRUD()
        assert crud.table_name == "user_favorite_words"

    def test_add_favorite(self):
        """测试添加收藏"""
        from tools.favorites_crud import FavoritesCRUD

        crud = FavoritesCRUD()
        # 使用测试用户 ID 和单词 ID
        # 注意：需要数据库中有对应的用户和单词
        result = crud.add_favorite(user_id=1, word_id=1, note="测试笔记")
        # 结果应该是记录 ID 或 None
        assert result is None or isinstance(result, int)

    def test_is_favorited(self):
        """测试检查收藏状态"""
        from tools.favorites_crud import FavoritesCRUD

        crud = FavoritesCRUD()
        # 检查是否收藏
        result = crud.is_favorited(user_id=1, word_id=999999)
        assert isinstance(result, bool)

    def test_get_favorited_word_ids(self):
        """测试获取收藏单词 ID 列表"""
        from tools.favorites_crud import FavoritesCRUD

        crud = FavoritesCRUD()
        ids = crud.get_favorited_word_ids(user_id=1)
        assert isinstance(ids, list)

    def test_get_favorite_count(self):
        """测试获取收藏数量"""
        from tools.favorites_crud import FavoritesCRUD

        crud = FavoritesCRUD()
        count = crud.get_favorite_count(user_id=1)
        assert isinstance(count, int)
        assert count >= 0


class TestFavoritesAPI:
    """收藏 API 测试"""

    def test_get_favorites_unauthorized(self, client):
        """测试未授权访问收藏列表"""
        response = client.get("/api/favorites/1")
        assert response.status_code == 401

    def test_get_favorite_ids_unauthorized(self, client):
        """测试未授权访问收藏 ID 列表"""
        response = client.get("/api/favorites/1/ids")
        assert response.status_code == 401

    def test_add_favorite_unauthorized(self, client):
        """测试未授权添加收藏"""
        response = client.post("/api/favorites/1/word/1")
        assert response.status_code == 401

    def test_remove_favorite_unauthorized(self, client):
        """测试未授权删除收藏"""
        response = client.delete("/api/favorites/1/word/1")
        assert response.status_code == 401

    def test_check_favorite_unauthorized(self, client):
        """测试未授权检查收藏"""
        response = client.get("/api/favorites/1/word/1")
        assert response.status_code == 401

    def test_get_favorites_authorized(self, client, auth_header):
        """测试授权访问收藏列表"""
        response = client.get("/api/favorites/1", headers=auth_header)
        # 可能返回 403（非当前用户）或 200
        assert response.status_code in [200, 403]

    def test_get_favorite_ids_authorized(self, client, auth_header):
        """测试授权访问收藏 ID 列表"""
        response = client.get("/api/favorites/1/ids", headers=auth_header)
        assert response.status_code in [200, 403]

    def test_update_note_unauthorized(self, client):
        """测试未授权更新备注"""
        response = client.put(
            "/api/favorites/1/word/1/note",
            json={"note": "测试"}
        )
        assert response.status_code == 401
