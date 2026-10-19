# 환경 설정 항목 전체표

확인일: 2026-10-19. `.env.example`·Compose·현재 설정 로더와 사용 코드를 대조했습니다. 신청 순서는 [README](../README.md), 사이트·분석 자료 목록은 [통합 TXT](API_KEYS_AND_DATA.txt)를 참고합니다.

## 파일과 반영 방식

- `.env.example`: 키·암호가 비어 있는 공유 양식. 이 파일을 직접 채워 커밋하지 않습니다.
- `.env`: 사용자가 복사·편집하는 실제 설정. `compose.yaml`과 같은 폴더에 둡니다.
- Docker: Compose가 `.env`를 읽어 `environment`에 선언된 항목만 `web`에 전달합니다. 파일 전체를 컨테이너에 복사하지 않습니다.
- Python: `python run_local.py`와 색인 실행기가 허용된 설정 이름을 읽습니다. `uvicorn backend.app:app`만 직접 실행하는 방식은 이 안내의 기본 경로가 아닙니다.
- 반영: 저장 → `docker compose up -d --build web` → 브라우저 새로고침. 단순 컨테이너 restart만으로 Compose 환경변수 변경이 반영되는 것은 아닙니다.
- 터미널에 이미 같은 환경변수가 있으면 `.env`보다 우선할 수 있습니다. 중복 줄·앞의 `#`·`.env.txt` 여부도 확인합니다.

## 현재 실행에 쓰는 항목

| 이름 | 값·기본 예제 | 실제 용도·판정 |
| --- | --- | --- |
| `APP_ENV` | `development` | Compose 전달용 구분값. 현재 앱은 이 값으로 개발/운영 기능을 자동 분리하지 않음 |
| `APP_PORT` | `8000` | 호스트 브라우저 접속 포트. 내부 컨테이너 포트는 8000 유지 |
| `ADMIN_USERNAME` | `admin` | 관리자 계정명 |
| `ADMIN_PASSWORD` | 빈칸 | 본인이 정하는 12자 이상 암호. API 발급키가 아님. Docker에서 비어 있으면 관리 로그인 불가 |
| `VWORLD_API_KEY` | 빈칸 | VWorld 오픈API 인증키. 영상 타일용 WMTS/TMS 권한 필요 |
| `VWORLD_DOMAIN` | 빈칸 | 등록된 서비스 URL을 명시할 때 사용. 비우면 현재 웹 기본 주소. 권한 변경·우회 기능 아님 |
| `OLLAMA_BASE_URL` | `http://host.docker.internal:11434` | Docker 웹에서 호스트 Ollama 연결. 직접 Python은 `http://127.0.0.1:11434` |
| `GREENZONE_AI_ENABLED` | `0` | `1`일 때 대화 모델로 질문 의도 분류. 문서 임베딩과 별개 |
| `OLLAMA_MODEL` | 빈칸 | 실제 설치 대화 모델 이름. 분류를 켤 때 입력. 임베딩 모델을 넣지 않음 |
| `OLLAMA_TIMEOUT_SECONDS` | `45` | 질문 분류 응답 시간 제한. 코드에서 2~120초로 제한 |
| `GREENZONE_EMBEDDING_ENABLED` | `0` | `1`일 때 문서 의미 검색 사용 설정. 벡터 생성은 별도 명령 |
| `EMBEDDING_MODEL` | `bge-m3:latest` | 실제 연결 서버에 설치한 임베딩 모델 이름과 일치시킴 |
| `EMBEDDING_OLLAMA_BASE_URL` | 빈칸 | 비우면 OLLAMA_BASE_URL 재사용. 별도 임베딩 서버가 있을 때만 설정 |
| `EMBEDDING_TIMEOUT_SECONDS` | `60` | 복사 양식은 첫 모델 로딩을 고려해 60초. 코드/Compose에서 이 변수가 없을 때의 대체값은 12초이며 코드 허용 범위는 1~60초 |
| `EMBEDDING_MIN_SCORE` | `0.55` | 검색 유사도 기준. 정답 확률이 아니며 질의로 조정 |
| `EMBEDDING_REVISION` | `1` | 모델 버전·양자화가 달라질 때 올리고 재색인 |

`GREENZONE_AI_ENABLED=0`과 `GREENZONE_EMBEDDING_ENABLED=0`을 유지해도 지도·필지 배정 조회·품목표·기본 안내를 사용합니다. 로컬 Ollama 방식에는 클라우드 API 키를 추가하지 않습니다.

## 현재 프리뷰에서는 사용하지 않는 준비용 이름

아래는 `.env.example`에서 **전부 주석 처리**했습니다. 입력해도 현재 Compose·웹·포함된 실행 스크립트가 원본을 자동 수집하지 않습니다.

| 이름 | 받을 값·출처 | 준비할 때 |
| --- | --- | --- |
| `BUILDING_API_SERVICE_KEY` | [건축HUB 서비스](https://www.data.go.kr/data/15134735/openapi.do) 활용 권한이 있는 공공데이터포털 서비스키 | 별도 건물대장 재수집. 상세 수집기의 URL 인코딩 경로와 맞춰 Decoding 키 기준 준비 |
| `KOSIS_API_KEY` | [KOSIS 공유서비스](https://kosis.kr/openapi/index/index.jsp) 인증키 | 별도 통계 API 수집. 파일 다운로드 분석이면 생략 가능 |
| `SGIS_CONSUMER_KEY` / `SGIS_CONSUMER_SECRET` | [SGIS](https://sgis.mods.go.kr/developer/html/main.html) 서비스 ID / 보안 Key | 소지역 통계·경계 API 연결. accessToken은 별도로 얻는 임시 토큰 |
| `JUSO_SEARCH_CONFIRM_KEY` | [도로명주소](https://business.juso.go.kr/addrlink/openApi/apiReqst.do) 검색 API 승인키 | 현재 자료 밖의 일반 주소 검색을 새로 구현할 때 |
| `JUSO_COORD_CONFIRM_KEY` | 같은 사이트 좌표제공 API 승인키 | 좌표제공 서비스 승인 조건을 확인하고 새 연결을 만들 때. 검색 키와 별개 |

VWorld 건물·도로 원본을 다시 수집하려면 같은 키라도 WMS/WFS 등 해당 원본 API 권한·레이어·범위·이용조건을 추가 확인합니다. 영상지도의 WMTS/TMS 권한만으로 모든 원본 데이터를 받는 것은 아닙니다.

## 별도 경로 설정과 저장 주의

기본 사용자는 `DEMO_DB_PATH`, `GREENZONE_CATALOG_PATH`를 바꿀 필요가 없습니다. Docker는 DB를 `/app/storage/demo.db`에 두고 이름 있는 볼륨으로 보관합니다. 로컬 실행기는 `storage/demo.db` 또는 기존 로컬 DB를 사용합니다. 관리자 수정·벡터는 실행 DB에 있으며 공유 저장소에 포함하지 않습니다.

분석 지도는 `data/pilot_analysis.json`, 카탈로그는 `data/analysis_result.json`, 품목표는 `data/waste_catalog.json`, 문서는 `data/knowledge_documents.json`을 사용합니다. 관리자 좌표 수정만으로 분석 지도·거리·권역이 자동 재계산되지는 않습니다.

## 값 노출 없이 확인하기

브라우저에서 아래 주소를 열면 실제 키값 없이 상태를 확인할 수 있습니다. APP_PORT를 바꿨다면 주소 포트도 변경합니다.

| 주소 | 알 수 있는 것 | 뜻하지 않는 것 |
| --- | --- | --- |
| `/health` | 웹 서버 응답 | 지도·AI·외부 API의 정상 작동 전체 |
| `/api/config` | 관리 암호 사용 조건·질문 분류 설정 여부 | 로그인 성공·모델 추론 성공 |
| `/api/map/config` | VWorld 키 설정 유무 | 키 승인·실제 타일 응답 성공 |
| `/api/knowledge/status` | 문서 수·현재 모델에 맞는 색인 수·완료 여부 | 실제 모델 서버 연결·검색 정확도 |
| `/api/ai/status` | 분류를 켰을 때 모델 목록 연결·모델 존재 | 실제 질문 분류 정확도. 꺼진 상태는 연결 실패와 다름 |

`docker compose config` 전체 출력이나 `.env` 내용에는 실제 키가 들어갈 수 있으므로 그대로 캡처·공유하지 않습니다. 문의에는 키를 지운 오류 종류와 설정 이름만 제공합니다.
