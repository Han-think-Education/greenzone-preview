"""Ollama 직접 연결: 실데이터 검증 없는 시연 안내는 절대로 실배출장소로 확정하지 않는다."""
from __future__ import annotations

import os
import re

import httpx

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
    host = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
    timeout = max(2, min(float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "45")), 120))
    request = {
        "model": model,
        "stream": False,
        "options": {"temperature": 0.1, "num_predict": 140},
        "messages": [
            {"role": "system", "content": (
                "너는 교육 시연용 분리배출 안내 AI다. 확정된 사실은 아래 한 문장뿐이다. "
                "확인되지 않은 위치, 동 이름, 실제 배출 시간/요일, 수거함 좌표, 예약 완료 등을 절대 만들어내지 마라. "
                "사용자에게 2문장으로 짧게 답하되 확인되지 않은 정보는 검증이 필요하다고 명시해라. "
                f"확인된 안전 안내: {verified_guidance}")},
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


async def ollama_status() -> dict:
    host = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11435").rstrip("/")
    model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")
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
