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
    from ai_travel_agent.memory import ShortTermMemory, remember_thread

    with TestClient(app) as client:
        token = auth_token(client, "13900000009")
        headers = {"Authorization": f"Bearer {token}"}
        trip_id = db.save_trip("13900000009", "th-trips", {"destination": "京都"}, "# 京都 3 天行程")
        ShortTermMemory("th-trips").append("user", "京都 3 天")
        remember_thread("13900000009", "th-trips")

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
        # 删行程时对应的会话也一起删掉，历史对话里不留孤儿
        assert client.get("/api/threads", headers=headers).json()["items"] == []
        assert client.get("/api/trips").status_code == 401


def test_save_trip_keeps_latest_per_thread():
    from ai_travel_agent import db

    db.init_db()
    db.save_trip("13900000011", "th-dup", {"destination": "巴黎"}, "# 旧行程")
    db.save_trip("13900000011", "th-dup", {"destination": "巴黎"}, "# 新行程")

    items = db.list_trips("13900000011")
    assert len(items) == 1
    assert "新行程" in items[0]["plan"]


def test_thread_history_list_messages_and_delete():
    from ai_travel_agent.memory import ShortTermMemory, remember_thread

    with TestClient(app) as client:
        token = auth_token(client, "13900000013")
        headers = {"Authorization": f"Bearer {token}"}
        mem = ShortTermMemory("hist-1")
        mem.append("user", "我想去上海玩5天")
        mem.append("assistant", "# 上海 5 天行程")
        remember_thread("13900000013", "hist-1")

        items = client.get("/api/threads", headers=headers).json()["items"]
        assert items and items[0]["thread_id"] == "hist-1"
        assert "上海" in items[0]["title"]
        assert items[0]["message_count"] == 2
        assert items[0]["updated_at"] > 0

        msgs = client.get("/api/threads/hist-1/messages", headers=headers).json()["messages"]
        assert [m["role"] for m in msgs] == ["user", "assistant"]
        assert client.get("/api/threads/hist-1/messages", headers=headers).json()["pending"] is None

        other = auth_token(client, "13900000014")
        other_headers = {"Authorization": f"Bearer {other}"}
        assert client.get("/api/threads/hist-1/messages", headers=other_headers).status_code == 404
        assert client.delete("/api/threads/hist-1", headers=other_headers).status_code == 404

        assert client.delete("/api/threads/hist-1", headers=headers).status_code == 200
        assert client.get("/api/threads", headers=headers).json()["items"] == []
        assert client.get("/api/threads").status_code == 401
