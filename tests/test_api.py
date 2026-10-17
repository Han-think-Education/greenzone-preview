"""pytest -q: 시연용 API 핵심 기능 검증."""
import os
import tempfile
from pathlib import Path

# 테스트 DB 분리: 로컬 개발 데이터를 건드리지 않도록 테스트 import보다 먼저 경로 설정.
_tmp_dir = tempfile.TemporaryDirectory()
os.environ["DEMO_DB_PATH"] = str(Path(_tmp_dir.name) / "test.db")

from fastapi.testclient import TestClient  # noqa: E402
from backend.app import app  # noqa: E402

client = TestClient(app)


def test_health():
    assert client.get("/health").json() == {"status": "ok", "preview": True}


def test_zones_and_buildings():
    assert len(client.get("/api/zones").json()) == 3
    assert len(client.get("/api/buildings").json()) == 24
    assert len(client.get("/api/buildings?zone=A").json()) == 8


def test_match_requires_existing_building():
    response = client.post("/api/match", json={"building_id": "NOT-EXIST", "category": "general"})
    assert response.status_code == 404


def test_match_no_fake_location():
    response = client.post("/api/match", json={"building_id": "A-01", "category": "battery"})
    assert response.status_code == 200
    body = response.json()
    assert body["matched_point"] is None
    assert body["verification_status"] == "unverified"


def test_invalid_category_rejected():
    response = client.post("/api/match", json={"building_id": "A-01", "category": "unknown"})
    assert response.status_code == 422


def test_request_not_real_booking():
    response = client.post("/api/requests", json={"building_id": "A-01", "category": "bulky", "quantity": 2})
    assert response.status_code == 201
    assert response.json()["status"] == "demo_only"


def test_preview_renders():
    response = client.get("/")
    assert response.status_code == 200
    assert "그린존" in response.text


def test_chat_unknown_does_not_default_to_general():
    response = client.post("/api/chat", json={"message": "오늘 점심 메뉴 뭐야?"})
    assert response.status_code == 200
    data = response.json()
    assert data["category"] is None
    assert data["mode"] == "needs_clarification"
    assert data["ai_used"] is False


def test_chat_ollama_unavailable_uses_safe_fallback(monkeypatch):
    async def unavailable(*args, **kwargs):
        raise ConnectionError("fake offline")
    monkeypatch.setattr("backend.app.query_ollama", unavailable)
    response = client.post("/api/chat", json={"message": "의자 버리고 싶어"})
    data = response.json()
    assert data["category"] == "bulky"
    assert data["mode"] == "fallback"
    assert data["ai_used"] is False
    assert "스마트" not in data["response"] or "https://smartclean.yangcheon.go.kr/" in data["response"]


def test_chat_ollama_success(monkeypatch):
    async def answer(*args, **kwargs):
        return "품목별 안내가 필요합니다."
    monkeypatch.setattr("backend.app.query_ollama", answer)
    response = client.post("/api/chat", json={"message": "폐건전지 어떻게 버려?"})
    data = response.json()
    assert data["category"] == "battery"
    assert data["mode"] == "ollama"
    assert data["ai_used"] is True
    assert "검증된" in data["response"]


def test_chat_input_validation():
    assert client.post("/api/chat", json={"message": ""}).status_code == 422
    assert client.post("/api/chat", json={"message": "가" * 501}).status_code == 422
