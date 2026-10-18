"""실행기와 문서 색인 작업에서 공유하는 로컬 설정 로더."""
import os
from pathlib import Path

EMBEDDING_KEYS = {
    "GREENZONE_EMBEDDING_ENABLED", "EMBEDDING_MODEL", "EMBEDDING_OLLAMA_BASE_URL",
    "EMBEDDING_TIMEOUT_SECONDS", "EMBEDDING_MIN_SCORE", "EMBEDDING_REVISION",
}


def load_local_environment(root: Path) -> None:
    allowed = EMBEDDING_KEYS | {
        "APP_PORT", "DEMO_DB_PATH", "GREENZONE_CATALOG_PATH", "ADMIN_USERNAME",
        "ADMIN_PASSWORD", "GREENZONE_AI_ENABLED", "OLLAMA_BASE_URL", "OLLAMA_MODEL",
        "OLLAMA_TIMEOUT_SECONDS", "VWORLD_API_KEY", "VWORLD_DOMAIN",
    }
    path = root / ".env"
    if path.exists():
        for line in path.read_text(encoding="utf-8-sig").splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key in allowed:
                os.environ.setdefault(key, value.strip().strip('"').strip("'"))
