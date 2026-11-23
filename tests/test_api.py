from fastapi.testclient import TestClient

from ai_travel_agent.api import app


def auth_token(client: TestClient, phone: str) -> str:
    code_resp = client.post("/api/auth/send-code", json={"phone": phone})
    assert code_resp.status_code == 200, code_resp.text
    code = code_resp.json()["dev_code"]
    login = client.post("/api/auth/login", json={"phone": phone, "code": code})
    assert login.status_code == 200, login.text
    return login.json()["token"]


def test_health_and_status():
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["status"] == "healthy"
        status = client.get("/api/status")
        assert status.status_code == 200
        assert "deepseek" in status.json()


def test_auth_flow_and_rag_search():
    with TestClient(app) as client:
        token = auth_token(client, "13900000003")
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 200
        assert me.json()["phone"] == "13900000003"
        rag = client.post(
            "/api/rag/search",
            json={"query": "巴黎 博物馆", "top_k": 2},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert rag.status_code == 200
        assert rag.json()["results"]


def test_stream_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/api/stream/t1", params={"message": "巴黎5天"})
        assert resp.status_code == 401
