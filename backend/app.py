"""5-day MVP FastAPI scaffold. 모든 건물·시설 데이터는 시연용 가상 데이터."""
from __future__ import annotations

import os
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Request, Response, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field, ConfigDict

from backend.chat_service import CATEGORY_GUIDES, identify_category, identify_topic, parse_ai_intent, ollama_status, query_ollama
from backend.catalog import add_tables, read_catalog, now_iso
from backend import auth

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DEMO_DB_PATH", str(Path(__file__).with_name("demo.db"))))
CATEGORIES = {"general": "일반 생활폐기물", "recycle": "재활용품", "battery": "폐건전지", "bulky": "대형폐기물"}
CATALOG_PATH = Path(os.getenv("GREENZONE_CATALOG_PATH", str(ROOT / "data/analysis_result.json")))


@contextmanager
def connection():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA foreign_keys = ON")
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def bootstrap() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with connection() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS zones (
            zone_id TEXT PRIMARY KEY,
            zone_name TEXT NOT NULL,
            is_verified INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS buildings (
            building_id TEXT PRIMARY KEY,
            zone_id TEXT NOT NULL REFERENCES zones(zone_id),
            building_name TEXT NOT NULL,
            road_address TEXT NOT NULL,
            verification_status TEXT NOT NULL DEFAULT 'unverified'
        );
        CREATE TABLE IF NOT EXISTS disposal_requests (
            request_id INTEGER PRIMARY KEY AUTOINCREMENT,
            building_id TEXT NOT NULL REFERENCES buildings(building_id),
            category TEXT NOT NULL,
            quantity INTEGER NOT NULL CHECK(quantity >= 1 AND quantity <= 99),
            status TEXT NOT NULL DEFAULT 'demo_only',
            created_at TEXT NOT NULL
        );
        """)
        count = db.execute("SELECT COUNT(*) FROM zones").fetchone()[0]
        if not count and not CATALOG_PATH.exists():
            db.executemany("INSERT INTO zones (zone_id, zone_name) VALUES (?, ?)",
                           [(z, f"ZONE {z} (가상)") for z in "ABC"])
            db.executemany(
                "INSERT INTO buildings (building_id, zone_id, building_name, road_address) VALUES (?,?,?,?)",
                [(f"{z}-{i:02d}", z, f"데모 빌라 {z}-{i:02d}", f"ZONE-{z} 시연용 가상 주소")
                 for z in "ABC" for i in range(1, 9)]
            )
        add_tables(db, CATALOG_PATH)


bootstrap()
app = FastAPI(title="GreenZone Preview API — 교육용 프로젝트", version="0.4.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


class MatchInput(BaseModel):
    building_id: str = Field(min_length=1, max_length=32)
    category: Literal["general", "recycle", "battery", "bulky"]
    quantity: int = Field(default=1, ge=1, le=99)
    plan_id: Literal["A", "B"] = "B"


class RequestInput(MatchInput):
    pass


def get_building(building_id: str) -> dict:
    with connection() as db:
        row = db.execute("SELECT * FROM buildings WHERE building_id = ?", (building_id,)).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="건물을 찾을 수 없습니다")
    return dict(row)


@app.get("/health")
def health():
    return {"status": "ok", "preview": True}


@app.get("/api/zones")
def zones():
    with connection() as db:
        return [dict(row) for row in db.execute("SELECT * FROM zones ORDER BY zone_id")]


@app.get("/api/buildings")
def buildings(zone: str | None = None):
    with connection() as db:
        if zone:
            return [dict(row) for row in db.execute(
                "SELECT * FROM buildings WHERE zone_id = ? ORDER BY building_id", (zone.upper(),))]
        return [dict(row) for row in db.execute("SELECT * FROM buildings ORDER BY building_id")]


@app.get("/api/buildings/{building_id}")
def building_detail(building_id: str):
    return get_building(building_id)


@app.get("/api/disposal-rules")
def disposal_rules():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM rules ORDER BY category")]


@app.get("/api/catalog")
def get_catalog():
    return read_catalog(connection)


@app.get("/api/candidates")
def candidates():
    return read_catalog(connection)["candidates"]


@app.get("/api/analysis")
def analysis():
    return read_catalog(connection)["analysis"]


@app.get("/api/config")
def configuration():
    return {"admin_configured": auth.configured(), "ai_enabled": os.getenv("GREENZONE_AI_ENABLED", "0") == "1", "version": "0.4.0"}


def match_logic(payload: MatchInput) -> dict:
    building = get_building(payload.building_id)
    messages = {
        "general": "건물별 허용된 배출 위치와 공식 배출 요일 확인이 필요합니다.",
        "recycle": "품목별 재활용 기준과 건물별 배출 위치를 확인해야 합니다.",
        "battery": "실제 운영이 확인된 전용 수거시설이 아직 등록되지 않았습니다.",
        "bulky": "양천구 공식 대형폐기물 배출 신고 절차를 확인하세요.",
    }
    data = read_catalog(connection)
    rule = next((r for r in data["rules"] if r["category"] == payload.category), None)
    plan = next((p for p in data["analysis"].get("plans", []) if p["plan_id"] == payload.plan_id), None)
    assignment = next((a for a in plan["assignments"] if a["building_id"] == building["building_id"]), None) if plan else None
    proposed = next((c for c in data["candidates"] if assignment and c["candidate_id"] == assignment["candidate_id"]), None)
    return {
        "building": building,
        "category": payload.category,
        "category_name": CATEGORIES[payload.category],
        "quantity": payload.quantity,
        "matched_point": None,
        "verification_status": "unverified",
        "guidance": rule["guidance"] if rule else messages[payload.category],
        "rule": rule,
        "proposed_candidate": proposed,
        "assignment": assignment,
        "official_url": "https://smartclean.yangcheon.go.kr/" if payload.category == "bulky" else None,
        "is_demo": True,
    }


@app.post("/api/match")
def match(payload: MatchInput):
    return match_logic(payload)


@app.get("/api/requests")
def list_requests():
    with connection() as db:
        return [dict(r) for r in db.execute(
            "SELECT * FROM disposal_requests ORDER BY request_id DESC LIMIT 100")]


@app.post("/api/requests", status_code=201)
def create_request(payload: RequestInput):
    match_logic(payload)  # 존재하는 건물인지 확인
    with connection() as db:
        cursor = db.execute(
            "INSERT INTO disposal_requests (building_id, category, quantity, created_at) VALUES (?,?,?,?)",
            (payload.building_id, payload.category, payload.quantity, datetime.now(timezone.utc).isoformat()),
        )
        request_id = cursor.lastrowid
    return {"request_id": request_id, "status": "demo_only", "message": "시연용 요청입니다. 실제 수거 예약이 아닙니다."}


class ChatInput(BaseModel):
    message: str = Field(min_length=1, max_length=500)
    building_id: str | None = Field(default=None, max_length=32)


@app.get("/api/ai/status")
async def ai_status():
    return await ollama_status()


@app.post("/api/chat")
async def chat(payload: ChatInput):
    category = identify_category(payload.message)
    if category is None:
        return {
            "category": None, "mode": "needs_clarification", "ai_used": False,
            "response": "품목을 판별하지 못했습니다. 일반쓰레기, 재활용품, 폐건전지, 대형폐기물 중 무엇인지 알려주세요.",
            "verification_status": "unverified", "is_demo": True,
        }

    guide = CATEGORY_GUIDES[category]
    topic = identify_topic(payload.message)
    mode, ai_used = "fallback", False
    try:
        generated = await query_ollama(payload.message, guide)
        intent = parse_ai_intent(generated)
        if intent["category"] not in (category, None):
            raise ValueError("품목 판정이 서로 다릅니다")
        topic = intent["topic"]
        mode, ai_used = "ollama", True
    except Exception:
        pass
    rule = next((r for r in disposal_rules() if r["category"] == category), None)
    response_text = rule["guidance"] if rule else guide
    if topic == "when":
        response_text += "\n배출 요일: " + ((rule or {}).get("days") or "공식 자료 확인 필요")
        response_text += "\n배출 시간: " + ((rule or {}).get("time_text") or "공식 자료 확인 필요")
    elif topic == "where":
        response_text += "\n현재 지도는 제안 후보입니다. 실제 배출 가능 장소로 확정하지 않습니다."
    if rule and rule.get("source_url"):
        response_text += "\n안내 출처: " + rule["source_url"]
    return {
        "category": category, "mode": mode, "ai_used": ai_used, "topic": topic,
        "response": response_text + "\n※ 시연용 서비스이며, 확인되지 않은 배출 위치를 안내하지 않습니다.",
        "verification_status": "unverified", "is_demo": True,
    }


class LoginInput(BaseModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=256)


def require_admin(request: Request):
    if not auth.valid(request.cookies.get("greenzone_session")):
        raise HTTPException(401, "담당자 로그인이 필요합니다")
    origin = request.headers.get("origin")
    if origin and origin.rstrip("/") != str(request.base_url).rstrip("/"):
        raise HTTPException(403, "같은 사이트에서 수정해 주세요")


@app.get("/api/auth/session")
def session(request: Request):
    return {"authenticated": auth.valid(request.cookies.get("greenzone_session")), "configured": auth.configured()}


@app.post("/api/auth/login")
def login(payload: LoginInput, request: Request, response: Response):
    if not auth.configured():
        raise HTTPException(503, "실행 환경에 12자 이상 관리자 암호를 설정해 주세요")
    token = auth.sign_in(payload.username, payload.password, request.client.host if request.client else "unknown")
    if not token:
        raise HTTPException(401, "로그인 정보를 확인해 주세요. 반복 실패 시 잠시 후 다시 시도해 주세요.")
    response.set_cookie("greenzone_session", token, max_age=auth.SESSION_SECONDS, httponly=True, samesite="strict", secure=request.url.scheme == "https")
    return {"authenticated": True}


@app.post("/api/auth/logout")
def logout(request: Request, response: Response):
    auth.sign_out(request.cookies.get("greenzone_session"))
    response.delete_cookie("greenzone_session")
    return {"authenticated": False}


class CandidatePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    review_status: Literal["review", "selected", "hold", "excluded"] | None = None
    rationale: str | None = Field(default=None, max_length=2000)
    safety_note: str | None = Field(default=None, max_length=2000)
    truck_access: Literal["pass", "fail", "unknown"] | None = None
    stopping_space: Literal["pass", "fail", "unknown"] | None = None
    work_space: Literal["pass", "fail", "unknown"] | None = None
    pedestrian_clear: Literal["pass", "fail", "unknown"] | None = None
    capacity: float | None = Field(default=None, ge=1, le=100000, allow_inf_nan=False)
    lat: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    lon: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)


class RulePatch(BaseModel):
    model_config = ConfigDict(extra="forbid")
    revision: int = Field(ge=1)
    days: str | None = Field(default=None, max_length=120)
    time_text: str | None = Field(default=None, max_length=120)
    guidance: str | None = Field(default=None, min_length=1, max_length=2000)
    source_url: str | None = Field(default=None, max_length=1500)
    reference_date: str | None = Field(default=None, max_length=40)


def update_record(table: str, key: str, entity_id: str, payload: BaseModel):
    values = payload.model_dump(exclude_unset=True)
    revision = values.pop("revision")
    if not values:
        raise HTTPException(422, "수정할 항목이 없습니다")
    # 빈 좌표·용량은 미확인으로 보류하되 NOT NULL 항목의 null 입력은 거부한다.
    for field in values:
        if values[field] is None and field not in ("lat", "lon", "capacity"):
            raise HTTPException(422, f"{field} 값이 비어 있습니다")
    if table == "rules" and values.get("source_url"):
        from urllib.parse import urlparse
        u = urlparse(values["source_url"])
        if u.scheme not in ("https", "http") or not u.netloc or u.username or u.password:
            raise HTTPException(422, "출처는 http 또는 https 주소로 입력해 주세요")
    with connection() as db:
        old = db.execute(f"SELECT * FROM {table} WHERE {key}=?", (entity_id,)).fetchone()
        if not old:
            raise HTTPException(404, "대상 자료가 없습니다")
        if old["revision"] != revision:
            raise HTTPException(409, "다른 수정이 반영되었습니다. 새로 불러온 뒤 다시 수정해 주세요")
        values["updated_at"] = now_iso()
        clauses = ",".join(f"{name}=?" for name in values)
        cursor = db.execute(f"UPDATE {table} SET {clauses},revision=revision+1 WHERE {key}=? AND revision=?", tuple(values.values()) + (entity_id, revision))
        if cursor.rowcount != 1:
            raise HTTPException(409, "최신 자료를 다시 불러와 주세요")
        db.execute("INSERT INTO change_history (entity_type,entity_id,changed_at,changes) VALUES (?,?,?,?)", (table, entity_id, now_iso(), json.dumps(values, ensure_ascii=False)))
        return dict(db.execute(f"SELECT * FROM {table} WHERE {key}=?", (entity_id,)).fetchone())


@app.patch("/api/admin/candidates/{candidate_id}", dependencies=[Depends(require_admin)])
def update_candidate(candidate_id: str, payload: CandidatePatch):
    return update_record("candidates", "candidate_id", candidate_id, payload)


@app.patch("/api/admin/rules/{rule_id}", dependencies=[Depends(require_admin)])
def update_rule(rule_id: str, payload: RulePatch):
    return update_record("rules", "rule_id", rule_id, payload)


@app.get("/api/admin/history", dependencies=[Depends(require_admin)])
def history():
    with connection() as db:
        return [dict(r) for r in db.execute("SELECT * FROM change_history ORDER BY change_id DESC LIMIT 30")]


# API 라우트를 먼저 등록한 후 static 파일을 마운트합니다.
@app.get("/admin", include_in_schema=False)
@app.get("/admin/", include_in_schema=False)
def admin_page():
    return FileResponse(ROOT / "preview" / "admin.html")


app.mount("/", StaticFiles(directory=str(ROOT / "preview"), html=True), name="preview")
