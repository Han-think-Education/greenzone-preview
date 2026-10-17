"""Ollama 직접 연결: 실데이터 검증 없는 시연 안내는 절대로 실배출장소로 확정하지 않는다."""
from __future__ import annotations

import os
import re
import json

CATEGORY_GUIDES = {
    "general": "일반 생활폐기물은 건물별 허용된 배출 위치와 구청 공식 배출 일정을 확인해야 합니다.",
    "recycle": "재활용품은 품목별 분리배출 규칙과 해당 건물의 배출 위치를 확인해야 합니다.",
    "battery": "폐건전지는 검증된 전용 수거함 정보가 아직 등록되지 않아 실제 장소를 추천할 수 없습니다.",
    "bulky": "가구 등 대형폐기물은 구청 공식 신고 절차를 통해 접수해야 합니다. https://smartclean.yangcheon.go.kr/",
}


def identify_category(message: str) -> str | None:
    # 기초적인 결정론적 분류. 알 수 없는 입력을 임의로 일반쓰레기로 정하지 않는다.
    rules = (
        ("battery", r"건전지|배터리|폐전지"),
        ("bulky", r"의자|책상|소파|침대|가구|대형폐기물"),
        ("recycle", r"재활용|분리수거|플라스틱|페트병|캔|종이"),
        ("general", r"일반쓰레기|종량제|생활폐기물|쓰레기|배출|버리"),
    )
    for category, pattern in rules:
        if re.search(pattern, message, re.IGNORECASE):
            return category
    return None


async def query_ollama(message: str, verified_guidance: str) -> str:
    if os.getenv("GREENZONE_AI_ENABLED", "0") != "1":
        raise RuntimeError("AI는 선택 기능이며 현재 꺼져 있습니다")
    import httpx
    host = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "").strip()
    if not model:
        raise ValueError("실제로 사용할 모델 이름을 설정해 주세요")
    timeout = max(2, min(float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")), 120))
    request = {
        "model": model,
        "stream": False,
        "format": "json",
        "options": {"temperature": 0, "num_predict": 100},
        "messages": [
            {"role": "system", "content": (
                "너는 분리배출 질문 분류기다. 답변 문장을 작성하지 말고 JSON만 반환해라. "
                '형식은 {"category":"general|recycle|battery|bulky|unknown","topic":"when|where|how|source|unknown"}다. '
                "품목과 질문 의도만 판단한다. 위치·시간·요일·URL·설명 필드는 절대 출력하지 않는다.")},
            {"role": "user", "content": message},
        ],
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        response = await client.post(host + "/api/chat", json=request)
        response.raise_for_status()
        text = response.json().get("message", {}).get("content", "")
        if not isinstance(text, str) or not text.strip():
            raise ValueError("Ollama returned empty content")
        return text.strip()[:900]


def identify_topic(message: str) -> str:
    if re.search(r"언제|요일|시간|몇 시", message):
        return "when"
    if re.search(r"어디|장소|위치|수거함", message):
        return "where"
    if re.search(r"출처|근거|공식", message):
        return "source"
    return "how"


def parse_ai_intent(text: str) -> dict:
    # 기존 프리뷰의 고정 안내문도 사실을 생성하지 않는 호환값으로만 허용한다.
    if text.strip() == "품목별 안내가 필요합니다.":
        return {"category": None, "topic": "how"}
    data = json.loads(text)
    if not isinstance(data, dict) or set(data) != {"category", "topic"}:
        raise ValueError("허용되지 않은 AI 출력 필드")
    if data["category"] not in {"general", "recycle", "battery", "bulky", "unknown"}:
        raise ValueError("허용되지 않은 품목")
    if data["topic"] not in {"when", "where", "how", "source", "unknown"}:
        raise ValueError("허용되지 않은 질문 의도")
    return {"category": None if data["category"] == "unknown" else data["category"], "topic": data["topic"]}


async def ollama_status() -> dict:
    model = os.getenv("OLLAMA_MODEL", "")
    if os.getenv("GREENZONE_AI_ENABLED", "0") != "1":
        return {"connected": False, "model": model, "model_installed": False, "message": "규칙 기반 안내 · AI 선택 기능 꺼짐"}
    try:
        import httpx
    except ImportError:
        return {"connected": False, "model": model, "model_installed": False, "message": "AI 연결 패키지 준비 필요 · 기본 안내 사용"}
    host = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            response = await client.get(host + "/api/tags")
            response.raise_for_status()
        available = [entry.get("name", "") for entry in response.json().get("models", [])]
        installed = model in available or any(name.startswith(model + ":") for name in available)
        return {"connected": True, "model": model, "model_installed": installed,
                "message": "모델 사용 준비됨" if installed else "Ollama는 연결되었으나 모델 다운로드 필요"}
    except (httpx.HTTPError, ValueError):
        return {"connected": False, "model": model, "model_installed": False,
                "message": "Ollama 연결 안 됨 — 규칙 기반 대체 응답 사용"}
