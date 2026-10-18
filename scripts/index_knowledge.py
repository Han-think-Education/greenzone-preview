"""안내문 파일 등록. --embed를 명시한 경우에만 Ollama로 벡터를 만든다."""
from pathlib import Path
import argparse
import asyncio
from contextlib import contextmanager
import json
import os
import sqlite3
import sys
import httpx
from pydantic import ValidationError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.settings import load_local_environment
from backend import knowledge


async def index(connection, use_embedding):
    with connection() as db:
        knowledge.create_tables(db)
        count = knowledge.sync_documents(db)
    print(f"안내문 등록: {count}개 문단")
    if not use_embedding:
        print("키워드 검색 준비 완료. 모델 호출 없음. 벡터 생성은 --embed로 별도 실행합니다.")
        return
    settings = knowledge.embedding_settings()
    if not settings["enabled"]:
        raise ValueError(".env의 GREENZONE_EMBEDDING_ENABLED=1 설정 후 다시 실행하세요.")
    with connection() as db:
        rows = db.execute("""SELECT c.* FROM knowledge_chunks c LEFT JOIN knowledge_embeddings e
            ON e.chunk_id=c.chunk_id AND e.content_hash=c.content_hash AND e.model_fingerprint=?
            WHERE e.chunk_id IS NULL""", (settings["fingerprint"],)).fetchall()
    written = 0
    for start in range(0, len(rows), 16):
        batch = rows[start:start + 16]
        texts = []
        for row in batch:
            doc = json.loads(row["payload"])
            texts.append(doc["title"] + "\n" + doc["text"])
        vectors = await knowledge.embed(texts, settings)
        with connection() as db:
            for row, vector in zip(batch, vectors):
                # 색인 중 원문이 바뀌었으면 이전 벡터를 새 원문에 붙이지 않는다.
                cursor = db.execute("""INSERT INTO knowledge_embeddings
                    SELECT chunk_id,?,content_hash,? FROM knowledge_chunks WHERE chunk_id=? AND content_hash=?
                    ON CONFLICT(chunk_id,model_fingerprint) DO UPDATE SET
                    content_hash=excluded.content_hash,vector=excluded.vector""",
                    (settings["fingerprint"], json.dumps(vector), row["chunk_id"], row["content_hash"]))
                written += cursor.rowcount
    print(f"벡터 저장: {written}개. 같은 원문·모델 설정은 다시 호출하지 않습니다.")


def main():
    load_local_environment(ROOT)
    previous_db = ROOT / "backend/demo.db"
    default_db = os.getenv("DEMO_DB_PATH") or str(previous_db if previous_db.exists() else ROOT / "storage/demo.db")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=Path(default_db))
    parser.add_argument("--embed", action="store_true", help="Ollama 임베딩 호출을 명시적으로 실행")
    args = parser.parse_args()
    args.db.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connection():
        db = sqlite3.connect(args.db)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    try:
        asyncio.run(index(connection, args.embed))
    except httpx.TimeoutException:
        print("색인 미완료 [응답 시간 초과]: 모델 첫 로딩이 길 수 있습니다. EMBEDDING_TIMEOUT_SECONDS를 늘려 다시 실행하세요.", file=sys.stderr)
        return 1
    except (httpx.ConnectError, httpx.InvalidURL):
        print("색인 미완료 [Ollama 연결]: 모델 서버 실행 상태와 EMBEDDING_OLLAMA_BASE_URL의 주소·포트를 확인하세요.", file=sys.stderr)
        return 1
    except httpx.HTTPStatusError as error:
        print(f"색인 미완료 [Ollama HTTP {error.response.status_code}]: 설치 모델명과 /api/embed 지원 여부를 확인하세요.", file=sys.stderr)
        return 1
    except sqlite3.Error:
        print("색인 미완료 [DB 저장]: SQLite 경로·쓰기 권한·다른 색인 작업 실행 여부를 확인하세요.", file=sys.stderr)
        return 1
    except ValidationError:
        print("색인 미완료 [문서 형식]: knowledge_documents.json의 필수 필드·날짜·URL을 확인하세요.", file=sys.stderr)
        return 1
    except ValueError as error:
        # 직접 작성한 설정·벡터 검증 메시지만 출력. JSON 응답 원문은 표시하지 않는다.
        if type(error) is ValueError:
            print("색인 미완료 [설정·벡터]: " + str(error), file=sys.stderr)
        else:
            print("색인 미완료 [응답 형식]: 원문 JSON 또는 Ollama 응답 형식을 확인하세요.", file=sys.stderr)
        return 1
    except Exception:
        # HTTP 오류에 포함될 수 있는 서버 URL·인증정보·원문 응답은 출력하지 않는다.
        print("색인 미완료 [기타]: 문서 파일과 Ollama 설정을 확인하세요. 기존 안내문은 키워드로 검색할 수 있습니다.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
