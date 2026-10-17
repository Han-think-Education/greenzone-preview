"""5-day MVP FastAPI scaffold. 모든 건물·시설 데이터는 시연용 가상 데이터."""
from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.chat_service import CATEGORY_GUIDES, identify_category, ollama_status, query_ollama

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("DEMO_DB_PATH", str(Path(__file__).with_name("demo.db"))))
CATEGORIES = {"general": "일반 생활폐기물", "recycle": "재활용품", "battery": "폐건전지", "bulky": "대형폐기물"}


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
        if not count:
            db.executemany("INSERT INTO zones (zone_id, zone_name) VALUES (?, ?)",
                           [(z, f"ZONE {z} (가상)") for z in "ABC"])
            db.executemany(
                "INSERT INTO buildings (building_id, zone_id, building_name, road_address) VALUES (?,?,?,?)",
                [(f"{z}-{i:02d}", z, f"데모 빌라 {z}-{i:02d}", f"ZONE-{z} 시연용 가상 주소")
                 for z in "ABC" for i in range(1, 9)]
            )


bootstrap()
app = FastAPI(title="GreenZone Preview API — 교육용 프로젝트", version="0.2.0")
app.add_middleware(CORSMiddleware, allow_origins=["http://127.0.0.1:5500", "http://localhost:5500"],
                   allow_methods=["GET", "POST"], allow_headers=["*"])


class MatchInput(BaseModel):
    building_id: str = Field(min_length=1, max_length=32)
    category: Literal["general", "recycle", "battery", "bulky"]
    quantity: int = Field(default=1, ge=1, le=99)


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
    return [{"category": key, "label": value, "verification_status": "unverified",
             "guidance": "실제 배출 장소·시간은 공식 자료 검증 후 등록"} for key, value in CATEGORIES.items()]


def match_logic(payload: MatchInput) -> dict:
    building = get_building(payload.building_id)
    messages = {
        "general": "건물별 허용된 배출 위치와 공식 배출 요일 확인이 필요합니다.",
        "recycle": "품목별 재활용 기준과 건물별 배출 위치를 확인해야 합니다.",
        "battery": "실제 운영이 확인된 전용 수거시설이 아직 등록되지 않았습니다.",
        "bulky": "양천구 공식 대형폐기물 배출 신고 절차를 확인하세요.",
    }
    return {
        "building": building,
        "category": payload.category,
        "category_name": CATEGORIES[payload.category],
        "quantity": payload.quantity,
        "matched_point": None,
        "verification_status": "unverified",
        "guidance": messages[payload.category],
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
    try:
        # LLM에는 이미 선택한 안전 안내만 제공합니다. DB 위치 데이터는 시연용이며 주입하지 않습니다.
        generated = await query_ollama(payload.message, guide)
        response_text = generated + "\n\n[필수 확인] " + guide
        mode, ai_used = "ollama", True
    except Exception:
        # LLM 장애가 서비스 장애로 전파되지 않도록 강등한다. 내부 예외는 클라이언트에 노출하지 않는다.
        response_text = guide
        mode, ai_used = "fallback", False
    return {
        "category": category, "mode": mode, "ai_used": ai_used,
        "response": response_text + "\n※ 시연용 서비스이며, 확인되지 않은 배출 위치를 안내하지 않습니다.",
        "verification_status": "unverified", "is_demo": True,
    }


# API 라우트를 먼저 등록한 후 static 파일을 마운트합니다.
app.mount("/", StaticFiles(directory=str(ROOT / "preview"), html=True), name="preview")
