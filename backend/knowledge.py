"""공식 안내 요약 검색. 생성형 답변 없이 근거·범위를 함께 반환한다."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
from urllib.parse import urlparse

import httpx
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DOCUMENT_PATH = Path(__file__).resolve().parents[1] / "data/knowledge_documents.json"
CATEGORIES = {"general", "recycle", "battery", "bulky"}


def today_kst():
    return datetime.now(timezone(timedelta(hours=9))).date()


class KnowledgeDocument(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    title: str = Field(min_length=1, max_length=200)
    text: str = Field(min_length=1, max_length=10000)
    district_code: str = Field(pattern=r"^(ALL|[0-9]{5})$")
    district_name: str = Field(min_length=1, max_length=100)
    dongs: list[str] = Field(default_factory=list, max_length=100)
    category: str
    keywords: list[str] = Field(default_factory=list, max_length=40)
    source_url: str
    checked_at: date
    reference_date: date | None = None
    effective_from: date | None = None
    effective_until: date | None = None
    verification_status: str = "unverified"
    topics: list[str] = Field(default_factory=lambda: ['how', 'source'], max_length=4)

    @field_validator('topics')
    @classmethod
    def check_topics(cls, value):
        if any(t not in {'how','when','where','source'} for t in value):
            raise ValueError('질문 유형을 확인하세요')
        return value

    @field_validator("category")
    @classmethod
    def check_category(cls, value):
        if value not in CATEGORIES:
            raise ValueError("지원하지 않는 품목입니다")
        return value

    @field_validator("verification_status")
    @classmethod
    def check_verification(cls, value):
        if value not in {"source_checked", "unverified"}:
            raise ValueError("원문 확인 상태를 기록하세요")
        return value

    @field_validator("source_url")
    @classmethod
    def check_url(cls, value):
        parsed = urlparse(value)
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise ValueError("인증정보가 없는 HTTPS 원문 주소가 필요합니다")
        return value

    @model_validator(mode="after")
    def check_dates(self):
        if self.checked_at > today_kst():
            raise ValueError("확인일은 미래일 수 없습니다")
        if self.effective_from and self.effective_until and self.effective_until < self.effective_from:
            raise ValueError("시행 종료일을 확인하세요")
        return self


def create_tables(db):
    db.executescript("""
    CREATE TABLE IF NOT EXISTS knowledge_chunks (
        chunk_id TEXT PRIMARY KEY, document_id TEXT NOT NULL,
        payload TEXT NOT NULL, content_hash TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS knowledge_embeddings (
        chunk_id TEXT NOT NULL REFERENCES knowledge_chunks(chunk_id) ON DELETE CASCADE,
        model_fingerprint TEXT NOT NULL, content_hash TEXT NOT NULL, vector TEXT NOT NULL,
        PRIMARY KEY (chunk_id, model_fingerprint)
    );
    """)


def sync_documents(db, path: Path = DOCUMENT_PATH) -> int:
    """파일 전체 검증 후 검색 테이블만 갱신. 거점·규칙·기존 담당자 수정은 보존."""
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    docs = [KnowledgeDocument.model_validate(row) for row in data["documents"]]
    if len({d.document_id for d in docs}) != len(docs):
        raise ValueError("문서 ID가 중복됩니다")
    rows = []
    for doc in docs:
        # 수천 건용 문서 DB를 새로 도입하지 않고 작은 원문 요약부터 다룬다.
        for index, text in enumerate(chunk_text(doc.text)):
            payload = doc.model_dump(mode="json", exclude_unset=True)
            payload["text"] = text
            encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True)
            rows.append((f"{doc.document_id}:{index}", doc.document_id, encoded,
                         hashlib.sha256(encoded.encode()).hexdigest()))
    for row in rows:
        db.execute("""INSERT INTO knowledge_chunks VALUES (?,?,?,?) ON CONFLICT(chunk_id)
            DO UPDATE SET document_id=excluded.document_id, payload=excluded.payload,
            content_hash=excluded.content_hash""", row)
    valid_ids = {r[0] for r in rows}
    for row in db.execute("SELECT chunk_id FROM knowledge_chunks").fetchall():
        if row[0] not in valid_ids:
            db.execute("DELETE FROM knowledge_embeddings WHERE chunk_id=?", (row[0],))
            db.execute("DELETE FROM knowledge_chunks WHERE chunk_id=?", (row[0],))
    db.execute("""DELETE FROM knowledge_embeddings WHERE NOT EXISTS
        (SELECT 1 FROM knowledge_chunks c WHERE c.chunk_id=knowledge_embeddings.chunk_id
         AND c.content_hash=knowledge_embeddings.content_hash)""")
    return len(rows)


def chunk_text(text):
    # 문장·문단 경계에서 묶는다. 긴 한 문장은 임의로 잘라 조건을 잃지 않는다.
    result, current = [], ""
    for sentence in re.split(r"\n\s*\n|(?<=[.!?])\s+", text.strip()):
        if current and len(current) + len(sentence) + 1 > 700:
            result.append(current)
            current = ""
        current = (current + " " + sentence).strip()
    if current:
        result.append(current)
    return result


def embedding_settings():
    base = os.getenv("EMBEDDING_OLLAMA_BASE_URL") or os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    model = os.getenv("EMBEDDING_MODEL", "bge-m3:latest").strip()
    revision = os.getenv("EMBEDDING_REVISION", "1")
    fingerprint = hashlib.sha256(json.dumps([base.rstrip('/'), model, revision]).encode()).hexdigest()
    try:
        timeout = max(1, min(float(os.getenv("EMBEDDING_TIMEOUT_SECONDS", "12")), 60))
        minimum = float(os.getenv("EMBEDDING_MIN_SCORE", "0.55"))
        if not math.isfinite(timeout) or not math.isfinite(minimum) or not -1 <= minimum <= 1:
            raise ValueError()
    except ValueError:
        timeout, minimum = 12, 0.55
    return {"enabled": os.getenv("GREENZONE_EMBEDDING_ENABLED", "0") == "1",
            "base_url": base.rstrip('/'), "model": model, "fingerprint": fingerprint,
            "timeout": timeout, "minimum": minimum}


def normalized_vector(values):
    if not isinstance(values, list) or not 1 <= len(values) <= 16384:
        raise ValueError("벡터 형식이 올바르지 않습니다")
    if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in values):
        raise ValueError("벡터 값이 올바르지 않습니다")
    norm = math.sqrt(sum(v * v for v in values))
    if not math.isfinite(norm) or norm == 0:
        raise ValueError("벡터 길이가 올바르지 않습니다")
    return [v / norm for v in values]


async def embed(texts: list[str], settings: dict) -> list[list[float]]:
    if not settings["enabled"] or not settings["model"]:
        raise ValueError("임베딩 설정이 꺼져 있습니다")
    async with httpx.AsyncClient(timeout=settings["timeout"], trust_env=False) as client:
        response = await client.post(settings["base_url"] + "/api/embed", json={
            "model": settings["model"], "input": texts, "truncate": False,
        })
        response.raise_for_status()
        body = response.json()
        if not isinstance(body, dict):
            raise ValueError("임베딩 응답 형식이 올바르지 않습니다")
        vectors = body.get("embeddings")
    if not isinstance(vectors, list) or len(vectors) != len(texts):
        raise ValueError("임베딩 응답 수가 올바르지 않습니다")
    vectors = [normalized_vector(v) for v in vectors]
    if len({len(v) for v in vectors}) != 1:
        raise ValueError("임베딩 차원이 서로 다릅니다")
    return vectors


def eligible(doc: dict, district_code: str, category: str | None, dong: str | None) -> bool:
    today = today_kst().isoformat()
    return (doc["verification_status"] == "source_checked"
            and doc["district_code"] in {district_code, "ALL"}
            and (category is None or doc["category"] == category)
            and (not doc["dongs"] or dong in doc["dongs"])
            and (not doc["effective_from"] or doc["effective_from"] <= today)
            and (not doc["effective_until"] or today <= doc["effective_until"]))


def lexical_score(message, doc):
    query = re.sub(r"\s+", "", message.lower())
    words = doc["keywords"] + re.findall(r"[가-힣A-Za-z0-9]{2,}", doc["title"])
    return sum(1 for word in set(words) if word and re.sub(r"\s+", "", word.lower()) in query)


def requested_other_area(message: str, district_code: str) -> bool:
    # 수수료 DB의 지원 범위는 양천구. '작은가구' 같은 사물명을 지명으로 잡지 않는다.
    return district_code != '11470' or region_mismatch(message, district_code)


def region_mismatch(message: str, district_code: str) -> bool:
    districts = '종로구 중구 용산구 성동구 광진구 동대문구 중랑구 성북구 강북구 도봉구 노원구 은평구 서대문구 마포구 양천구 강서구 구로구 금천구 영등포구 동작구 관악구 서초구 강남구 송파구 강동구'.split()
    named = [name for name in districts if name in message]
    expected = {'11470': '양천구', '11500': '강서구'}.get(district_code)
    cities = re.findall(r"(?<![가-힣])([가-힣]{2,8}시)(?=에서|에|의|은|는|도|\s|[?.,!]|$)", message)
    metros = re.findall(r"(?<![가-힣])(부산|대구|인천|광주|대전|울산|세종|제주)(?=에서|에|의|은|는|도|\s|[?.,!]|$)", message)
    return any(name != expected for name in named) or any(city not in {"서울시", "서울특별시"} for city in cities) or bool(metros)


async def search(connection, message, district_code="11470", category=None, dong=None):
    mismatch = region_mismatch(message, district_code)
    from backend.chat_service import identify_topic
    topic = identify_topic(message)
    settings = embedding_settings()
    with connection() as db:
        rows = db.execute("""SELECT c.chunk_id,c.payload,c.content_hash,e.vector
            FROM knowledge_chunks c LEFT JOIN knowledge_embeddings e
            ON e.chunk_id=c.chunk_id AND e.content_hash=c.content_hash AND e.model_fingerprint=?""",
            (settings["fingerprint"],)).fetchall()
    pool = [(r, json.loads(r["payload"])) for r in rows]
    pool = [(r, d) for r, d in pool if eligible(d, district_code, category, dong)]
    pool = [(r, d) for r, d in pool if topic in d.get('topics', ['how','when','source'] if d['document_id']=='YC-BULKY-COLLECTION' else ['how','source'])
            and (not mismatch or d['district_code'] == 'ALL')]
    if not pool:
        return {"mode": "no_documents", "citations": [], "message": "이 지역·품목에서 원문이 확인된 안내가 아직 없습니다."}
    ranked, mode, message_out = [], "keyword", "문서 키워드 검색 · 임베딩 미사용"
    indexed = [(r, d) for r, d in pool if r["vector"]]
    if settings["enabled"] and len(indexed) == len(pool):
        try:
            query = (await embed([message], settings))[0]
            for row, doc in indexed:
                vec = json.loads(row["vector"])
                if len(vec) != len(query):
                    raise ValueError("재색인이 필요합니다")
                score = sum(x * y for x, y in zip(query, vec))
                if score >= settings["minimum"]:
                    ranked.append((score, row, doc))
            mode, message_out = "embedding", "BGE 문서 검색 · 유사도는 정답 확률이 아닙니다"
        except (httpx.HTTPError, httpx.InvalidURL, ValueError, KeyError, TypeError):
            ranked = []
            message_out = "임베딩 연결·색인 확인 필요 · 키워드 검색으로 안내"
    elif settings["enabled"]:
        message_out = "문서 벡터 색인 필요 · 키워드 검색으로 안내"
    if mode != "embedding":
        ranked = [(lexical_score(message, d), r, d) for r, d in pool]
        ranked = [entry for entry in ranked if entry[0] > 0]
    ranked.sort(key=lambda entry: (-entry[0], entry[1]["chunk_id"]))
    # 확실히 일치하는 품목·질문 키워드가 있으면 의미 검색의 인접 품목보다 먼저 제시한다.
    ranked.sort(key=lambda entry: (-(lexical_score(message, entry[2]) > 0),
                                  -lexical_score(message, entry[2]), -entry[0], entry[1]['chunk_id']))
    citations, seen = [], set()
    for score, row, doc in ranked:
        if doc["document_id"] in seen:
            continue
        seen.add(doc["document_id"])
        citations.append({**doc, "chunk_id": row["chunk_id"], "score": round(score, 4), "search_method": mode})
        if len(citations) == 3:
            break
    return {"mode": mode, "citations": citations, "message": message_out}


def status(connection):
    settings = embedding_settings()
    with connection() as db:
        count = db.execute("SELECT COUNT(*) FROM knowledge_chunks").fetchone()[0]
        indexed = db.execute("""SELECT COUNT(*) FROM knowledge_embeddings e JOIN knowledge_chunks c
            ON c.chunk_id=e.chunk_id AND c.content_hash=e.content_hash WHERE e.model_fingerprint=?""",
            (settings["fingerprint"],)).fetchone()[0]
    return {"embedding_enabled": settings["enabled"], "model": settings["model"],
            "chunk_count": count, "indexed_chunk_count": indexed,
            "index_complete": count > 0 and indexed == count,
            "connection_checked": False, "region": "양천구·강서구 운영 안내 및 전국 공통 분리 방법", "generation_enabled": False}
