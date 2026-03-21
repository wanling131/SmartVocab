"""健康检查 API 测试（不依赖 MySQL 时 /api/health 仍应通过）"""

import pytest


@pytest.fixture
def client():
    from api.api_launcher import create_api_launcher

    launcher = create_api_launcher()
    launcher.app.config["TESTING"] = True
    return launcher.app.test_client()


def test_health_ok(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    data = r.get_json()
    assert data.get("success") is True
    assert data.get("data", {}).get("status") == "ok"
