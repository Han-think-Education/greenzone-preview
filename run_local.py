"""간단한 로컬 실행. 패키지 설치·모델 다운로드·외부 게시를 자동 수행하지 않는다."""
from pathlib import Path
import argparse
import os
import secrets

ROOT = Path(__file__).resolve().parent
os.chdir(ROOT)
allowed = {"APP_PORT", "DEMO_DB_PATH", "GREENZONE_CATALOG_PATH", "ADMIN_USERNAME", "ADMIN_PASSWORD", "GREENZONE_AI_ENABLED", "OLLAMA_BASE_URL", "OLLAMA_MODEL", "OLLAMA_TIMEOUT_SECONDS"}
env_file = ROOT / ".env"
if env_file.exists():
    for line in env_file.read_text(encoding="utf-8-sig").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and key in allowed:
            os.environ.setdefault(key, value.strip().strip('"').strip("'"))

parser = argparse.ArgumentParser(description="그린존 로컬 시제품 실행")
parser.add_argument("--port", type=int, default=int(os.getenv("APP_PORT", "8000")))
args = parser.parse_args()
storage = ROOT / "storage"
storage.mkdir(exist_ok=True)
previous_db = ROOT / "backend/demo.db"
os.environ.setdefault("DEMO_DB_PATH", str(previous_db if previous_db.exists() else storage / "demo.db"))
os.environ.setdefault("GREENZONE_AI_ENABLED", "0")
os.environ.setdefault("ADMIN_USERNAME", "admin")
if not os.getenv("ADMIN_PASSWORD"):
    password = secrets.token_urlsafe(18)
    os.environ["ADMIN_PASSWORD"] = password
    (storage / "local-access.txt").write_text(
        f"그린존 로컬 접속정보\n주소: http://127.0.0.1:{args.port}\n아이디: {os.environ['ADMIN_USERNAME']}\n비밀번호: {password}\n\n이번 실행에서만 사용하는 암호입니다. 서버 재시작 시 바뀝니다.\n공개 저장소·화면 공유에 포함하지 마세요.\n", encoding="utf-8-sig")
    print("담당자 접속정보: storage/local-access.txt (공유하지 마세요)", flush=True)
elif len(os.environ["ADMIN_PASSWORD"]) < 12:
    raise SystemExit("ADMIN_PASSWORD를 12자 이상으로 설정해 주세요.")

if __name__ == "__main__":
    try:
        import uvicorn
    except ImportError:
        raise SystemExit("먼저 python -m pip install -r backend/requirements.txt 로 실행 패키지를 준비해 주세요.")
    print(f"Local: http://127.0.0.1:{args.port}", flush=True)
    uvicorn.run("backend.app:app", host="127.0.0.1", port=args.port, workers=1)
