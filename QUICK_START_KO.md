# 그린존 실행 안내

팀원에게 공유하는 5일 프로젝트용 프리뷰입니다. 신월1동·화곡1동의 수집·분석 결과를 웹에서 조회합니다. **분석 파일 제작과 웹 실행은 별도 작업**입니다.

처음 시작한다면 [README의 .env 생성·API 신청·입력 순서](README.md)를 먼저 읽으세요. [설정 전체표](docs/ENV_REFERENCE.md)에서 현재 사용하는 항목과 후속 수집용 주석 항목을 구분했습니다. 건축HUB·KOSIS 키는 현재 웹 실행에 필요하지 않습니다.

## 1. Docker로 시작하기 - 권장

준비: Docker Desktop(Windows는 WSL2 엔진 사용), Git. 별도 FastAPI 컨테이너·MariaDB·Node.js 설치는 필요하지 않습니다. `web` 컨테이너가 FastAPI와 화면을 제공하고 SQLite를 사용합니다.

```powershell
git clone https://github.com/Han-think-Education/greenzone-preview.git
cd greenzone-preview
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# 관리 기능을 쓰려면 .env의 ADMIN_PASSWORD를 12자 이상으로 설정
docker compose up -d --build web
```

이미 내려받았다면 프로젝트 폴더에서 `.env`를 유지한 채 마지막 명령으로 반영합니다. 최초 실행에는 이미지·Python 패키지 다운로드를 위한 인터넷 연결이 필요합니다.

| 화면 | 주소 | 할 수 있는 일 |
| --- | --- | --- |
| 사용자 지도 | http://localhost:8000/ | 지역 선택, 주소·건물명 검색, 제안 권역·조사점·방문 순서 확인 |
| 분석 결과 | http://localhost:8000/#analysis | 두 동의 수치·분석 가정·공식 출처 확인 |
| 배출도우미 | http://localhost:8000/#assistant | 품목·규격 확인, 공식 수수료·안내 원문 조회 |
| 관리자 | http://localhost:8000/admin | 설정한 계정으로 로그인 후 후보·규칙·확인 상태 수정 |

관리자 사용자명 기본값은 `admin`입니다. Docker에서는 암호를 자동 발급하지 않으며, `.env`에 12자 이상 설정해야 관리 로그인이 가능합니다. 암호가 없어도 일반 지도와 안내는 이용할 수 있습니다.

```powershell
# 코드·.env 변경 반영
docker compose up -d --build web
# 상태 및 최근 기록
docker compose ps
docker compose logs --tail 50 web
# 종료 - 저장 자료는 유지
docker compose down
```

SQLite는 이름 있는 Docker 볼륨에 보관됩니다. `docker compose down -v`는 DB 볼륨도 지우므로 사용하지 않습니다. `.env`·실행 DB·관리자 접속정보는 저장소에 포함하지 않습니다.

## 2. 필요한 설정만 선택

| 목적 | .env 항목 | 기본 동작 |
| --- | --- | --- |
| 일반지도·주소 검색·권역 조회·품목표 | 추가 키 없음 | 포함된 공식 자료 분석 파일 사용. 일반 배경지도는 인터넷 필요 |
| 위성·항공 / 영상+도로명 | `VWORLD_API_KEY` | 키가 없으면 영상 버튼 비활성. WMTS/TMS 권한·접속 주소 등록 확인 |
| 질문 분류 모델 | `GREENZONE_AI_ENABLED=1`, `OLLAMA_MODEL` | 기본 0. 모델 없이도 DB·기본 안내 이용 가능 |
| BGE 문서 검색 | `GREENZONE_EMBEDDING_ENABLED=1`, `EMBEDDING_MODEL` | 기본 0. 키워드 검색으로 이용 가능 |
| 원본 재수집 | 건축물대장·KOSIS 등 자료 키 | 웹 실행 필수 아님. 상세 조사 프로젝트에서 사용 |

영상지도 설정은 [영상지도 안내](docs/MAP_IMAGERY.md), 발급 사이트·자료 다운로드는 [통합 TXT](docs/API_KEYS_AND_DATA.txt)를 참고하세요. 기존 `.env`는 덮어쓰지 않습니다.

## 3. Ollama 연결 - 선택, 공유 기본 포트 11434

Ollama는 이 Compose에 포함되어 있지 않습니다. 팀원 컴퓨터에서 별도로 실행하고, 실제 설치 모델명을 확인합니다. 별도 모델을 임의로 자동 다운로드하지 않습니다.

```dotenv
# Docker 웹 → 호스트에서 실행 중인 Ollama
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=설치된_질문분류_모델명
GREENZONE_AI_ENABLED=0
# 문서 검색은 질문 분류와 별개
GREENZONE_EMBEDDING_ENABLED=0
EMBEDDING_MODEL=bge-m3:latest
# 비워 두면 OLLAMA_BASE_URL 사용
EMBEDDING_OLLAMA_BASE_URL=
```

Windows의 Docker 웹에서는 `host.docker.internal:11434`, 직접 Python 실행에서는 `127.0.0.1:11434`를 사용합니다. Ollama가 다른 컨테이너에 있다면 호스트 포트 11434로 연결되도록 해당 환경을 확인합니다. 팀의 실제 포트가 다르면 개인 `.env`만 변경합니다. 컨테이너 안의 `localhost`는 Windows 호스트를 뜻하지 않습니다.

BGE-M3를 설치했고 의미 검색을 쓰려면 `GREENZONE_EMBEDDING_ENABLED=1`로 바꾸고 아래 순서로 실행합니다. **색인 명령은 실제 Ollama 모델을 호출합니다.** 처음 로딩이 느리면 `EMBEDDING_TIMEOUT_SECONDS=60`으로 조정합니다.

```powershell
docker compose up -d --build web
docker compose exec web python -m scripts.index_knowledge --embed
```

`안내문 등록`과 `색인 완료`는 다릅니다. 미완료이면 서버 주소·모델명·응답 시간·문서 상태를 확인합니다. 상세 설정: [공식 문서 검색](docs/KNOWLEDGE_SEARCH.md).

## 4. 사용해 보기

1. 지도에서 신월1동 또는 화곡1동·까치산역을 선택합니다.
2. 도로명주소 또는 건물명으로 검색하고 원하는 주소를 클릭합니다.
3. 검색어·결과 목록은 비워지고 파란 집 표시와 담당 제안 조사점·권역이 남습니다.
4. 일반지도 / 위성·항공 / 영상+도로명을 전환해 같은 위치를 비교합니다.
5. 분석 화면에서 선정 근거·거리 구분·출처·추가 조사 항목을 봅니다.

현재 조사점은 **운영 승인 전 제안**입니다. 표시된 직선 연결은 보행 길안내가 아닙니다. 일방통행·차량 진입·정차·작업면·관리 동의를 확인한 실제 배출장소가 아닙니다. 관리자 수정과 별도 분석 파일 재계산도 자동으로 연결되지 않습니다.

## 5. Docker 없이 실행 - 대안

```powershell
python -m pip install -r backend/requirements.txt
python run_local.py
```

주소: http://127.0.0.1:8000/ . 다른 포트: `python run_local.py --port 8778`. Windows에서는 `START_GREENZONE.bat`도 사용합니다. 로컬 실행기가 자동 발급한 관리 접속정보는 `storage/local-access.txt`에서 확인합니다. 이 파일은 공유하지 않습니다. Docker DB와 로컬 Python DB는 기본 경로가 다릅니다. HTML 파일을 직접 열지 말고 서버 주소로 접속하세요.
