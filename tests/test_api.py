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
        assert health.json()["services"]["redis"] is True
        status = client.get("/api/status")
        assert status.status_code == 200
        assert status.json()["redis"] is True


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


def test_logout_endpoint_revokes_token():
    with TestClient(app) as client:
        token = auth_token(client, "13900000006")
        resp = client.post(
            "/api/auth/logout", headers={"Authorization": f"Bearer {token}"}
        )
        assert resp.status_code == 200
        me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert me.status_code == 401


def test_stream_requires_auth():
    with TestClient(app) as client:
        resp = client.get("/api/stream/t1", params={"message": "巴黎5天"})
        assert resp.status_code == 401


def test_trips_list_and_delete():
    from ai_travel_agent import db

    with TestClient(app) as client:
        token = auth_token(client, "13900000009")
        headers = {"Authorization": f"Bearer {token}"}
        trip_id = db.save_trip("13900000009", "th-trips", {"destination": "京都"}, "# 京都 3 天行程")

        items = client.get("/api/trips", headers=headers).json()["items"]
        assert [i["id"] for i in items] == [trip_id]
        assert "京都" in items[0]["plan"]
        assert items[0]["thread_id"] == "th-trips"

        other = auth_token(client, "13900000010")
        denied = client.delete(
            f"/api/trips/{trip_id}", headers={"Authorization": f"Bearer {other}"}
        )
        assert denied.status_code == 404

        assert client.delete(f"/api/trips/{trip_id}", headers=headers).status_code == 200
        assert client.get("/api/trips", headers=headers).json()["items"] == []
        assert client.get("/api/trips").status_code == 401


def test_save_trip_keeps_latest_per_thread():
    from ai_travel_agent import db

    db.init_db()
    db.save_trip("13900000011", "th-dup", {"destination": "巴黎"}, "# 旧行程")
    db.save_trip("13900000011", "th-dup", {"destination": "巴黎"}, "# 新行程")

    items = db.list_trips("13900000011")
    assert len(items) == 1
    assert "新行程" in items[0]["plan"]
