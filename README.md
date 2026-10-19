# GreenZone Preview

신월1동·화곡1동의 **공식 자료 분석 → 제안 수거 권역 → 주소 검색·지도 → 배출 안내**를 연결한 5일 팀프로젝트용 웹 시제품입니다. 아이디어를 실제 자료와 연결해 구현해 본 초기 가이드이며, 지도 조사점은 운영 승인을 받은 배출·정차 장소가 아닙니다.

[3쪽 화면 가이드 PDF](output/pdf/그린존_프리뷰_팀원_화면가이드.pdf) · [화면 캡처와 설명](docs/TEAM_PREVIEW_GUIDE.md) · [설정 항목 전체표](docs/ENV_REFERENCE.md) · [점검 결과](docs/PREVIEW_SETUP_AUDIT.md)

## 먼저: 무엇을 준비하나요?

| 원하는 기능 | 준비할 것 | 가입·API 키 |
| --- | --- | --- |
| 일반지도·주소/건물명 검색·제안 권역·품목표·기본 안내 | Git, Docker Desktop, 인터넷 연결 | **API 키 0개**. 분석 결과·품목·문서 파일 포함 |
| 관리자 수정 화면 | `.env`에서 직접 정한 12자 이상 암호 | 발급받는 키가 아님 |
| 위성·항공 / 영상+도로명 | VWorld 오픈API 인증키 | **VWorld 가입·키 발급, WMTS/TMS 권한** |
| BGE-M3 의미 검색 | 별도 Ollama 서버와 설치된 BGE-M3 | 로컬 모델은 API 키 없이 연결 |
| 질문 의도 AI 분류 | 별도 Ollama 서버와 설치된 대화 모델 | 로컬 모델은 API 키 없이 연결 |
| 건물·인구 자료 새로 수집·분석 | 건축HUB·KOSIS 등 원본과 별도 수집/분석 작업 | **현재 프리뷰 실행에는 불필요**. 아래 후속 준비 표 참고 |

`web` 컨테이너 하나가 **FastAPI + 웹 화면 + SQLite 접근**을 담당합니다. 별도 FastAPI 컨테이너·MariaDB·Node.js는 필요하지 않습니다. Ollama는 Compose에 들어 있지 않으므로 AI 기능을 쓸 때만 별도로 실행합니다. 영상지도·일반지도 배경과 최초 이미지/패키지 다운로드에는 인터넷이 필요합니다.

## 1. 저장소 내려받기

Docker Desktop을 설치·실행합니다. Windows에서는 Docker Desktop의 WSL2 엔진이 동작하는 환경을 준비합니다. 터미널은 PowerShell 예시입니다.

```powershell
git clone https://github.com/Han-think-Education/greenzone-preview.git
cd greenzone-preview
```

이미 내려받았다면 **기존 프로젝트 폴더에서** `git status`로 작업 여부를 확인하고 `git pull --ff-only`로 갱신합니다. 로컬 수정 때문에 실패하면 덮어쓰거나 초기화하지 말고 작업을 먼저 보관합니다.

## 2. `.env.example`을 읽고 `.env` 만들기

`.env.example`은 **공유하는 빈 설정 양식**, `.env`는 **본인 PC에서 실제 값으로 채우는 파일**입니다. 앱이 예제 파일을 자동으로 `.env`로 바꾸거나 API 키를 대신 발급하지 않습니다.

```powershell
# .env가 없을 때만 생성. 기존 키·암호를 덮어쓰지 않습니다.
if (-not (Test-Path -LiteralPath .env)) { Copy-Item .env.example .env }
# Windows 메모장으로 편집. VS Code에서는 왼쪽 파일 목록의 .env를 열어도 됩니다.
notepad .env
```

- 위치: `compose.yaml`, `README.md`와 **같은 폴더**.
- 이름: 정확히 **`.env`**. `.env.txt`로 저장하지 않습니다. Windows 탐색기의 파일 확장명 표시로 확인합니다.
- 형식: 한 줄에 `설정이름=값`. 앞에 `#`가 있으면 설명/비활성 줄입니다. 따옴표나 설명 문구까지 발급값으로 붙여 넣지 않습니다.
- 공백·`#`·`$`가 들어간 암호 등은 `.env` 값 전체를 작은따옴표로 감싸 Compose가 문자 그대로 읽도록 합니다. 실제 암호를 공유용 예제에 적지 않습니다.
- 관리자 기능을 쓴다면 `ADMIN_PASSWORD=` 오른쪽에 **본인이 정한 12자 이상 암호**를 넣고 저장합니다. `ADMIN_USERNAME=admin`은 기본 사용자명입니다.
- API를 쓰지 않을 때 키 입력란은 비워 둡니다. `여기에키입력` 같은 예시 문구를 실제 값으로 남기지 않습니다.
- Git에는 빈 `.env.example`만 공유합니다. **실제 키를 `.env.example`·README·캡처·이슈에 쓰지 않습니다.**

처음에는 `GREENZONE_AI_ENABLED=0`, `GREENZONE_EMBEDDING_ENABLED=0`을 유지해 기본 웹부터 실행하세요. `APP_PORT=8000`은 접속 포트입니다.

## 3. 기본 웹 시작하고 화면 확인하기

```powershell
docker compose up -d --build web
docker compose ps
```

| 화면 | 주소 | 기대하는 상태 |
| --- | --- | --- |
| 지도 | http://localhost:8000/ | 두 동의 제안 권역·조사점·주소 검색 |
| 분석 | http://localhost:8000/#analysis | 지역별 지표·출처·분석 가정 |
| 해우리 배출도우미 | http://localhost:8000/#assistant | 공식 품목표·확보된 안내. AI 없이도 기본 조회 가능 |
| 관리자 | http://localhost:8000/admin | 직접 설정한 계정으로 로그인. 암호 12자 미만이면 사용 불가 |
| 서버 상태 | http://localhost:8000/health | `status: ok` |

`APP_PORT=8001`로 바꿨다면 브라우저 주소도 `http://localhost:8001/`로 바꿉니다. 내부 FastAPI 포트 8000은 Compose가 연결합니다. HTML 파일을 직접 열지 말고 위 서버 주소로 접속합니다.

## 4. 위성·항공사진이 필요하면: VWorld 키 신청 → 입력

일반지도와 현재 건물 검색에는 필요하지 않습니다. 이 프리뷰에서 영상 배경에 사용하는 키는 **공공데이터포털 서비스키가 아니라 VWorld의 오픈API 인증키**입니다.

1. [VWorld](https://www.vworld.kr/)에서 회원가입·로그인합니다.
2. 개발자 안내의 **오픈API 인증키 발급/인증키 관리** 메뉴를 찾습니다. 로그인 뒤의 정확한 메뉴·항목명은 신청 화면에서 확인합니다.
3. 웹사이트용 서비스로 신청하고 **WMTS/TMS API** 사용 항목을 선택합니다. 현재 영상 배경에는 이 권한을 사용합니다. 3D·모바일·지오코더·검색 API는 지금 화면에 필수가 아닙니다.
4. 서비스 정보를 본인 프로젝트에 맞게 입력합니다. 아래는 교육용 기입 예시이며, 기관 소속을 임의로 적지 않습니다.

| 항목 | 기입 예시·확인 내용 |
| --- | --- |
| 서비스명 | 그린존 - 신월1동·화곡1동 제안 수거 권역 안내 |
| 서비스 유형 | 웹사이트 |
| 서비스 설명 | 공식 건물·도로 자료의 분석 결과를 지도에 표시하고 주소로 담당 제안 권역을 조회하는 교육용 시제품 |
| 서비스 URL | 실제 접속 주소. 로컬 실행은 `http://localhost:8000/` 사용 여부를 발급 화면의 허용 규칙에서 확인 |
| 활용 API | WMTS/TMS. 다른 자료 수집 권한은 해당 작업을 할 때 별도 검토 |
| 사용기관·활용사례 공개 등 | 본인 실제 상황과 동의 여부에 맞게 선택 |

5. 발급·승인 상태, 등록한 서비스 URL·허용 조건·유효기간·사용량을 확인합니다. 로컬 주소가 허용되지 않는다면 실제 허용된 개발/배포 주소를 준비해야 합니다. GitHub **저장소 주소는 실행 중인 서비스 URL과 다릅니다**. 다른 사이트 URL이나 임의 도메인으로 대체하지 않습니다.
6. 인증키를 복사해 **본인의 `.env`**에 입력합니다.

```dotenv
VWORLD_API_KEY=발급받은_VWorld_오픈API_인증키
# 등록 서비스 주소를 명시할 때만 입력. 비워 두면 현재 웹 기본 주소 사용.
VWORLD_DOMAIN=http://localhost:8000/
```

위 코드는 형식 설명입니다. `발급받은_...` 문구를 실제 인증키로 바꾸고, 도메인은 실제 등록·접속 주소에 맞춥니다. localhost와 127.0.0.1, 포트가 다르면 등록 조건도 확인합니다. `VWORLD_DOMAIN`은 권한을 우회하는 설정이 아닙니다.

7. 저장 후 `docker compose up -d --build web`을 실행하고 브라우저를 새로고침합니다.
8. 지도 위 **위성·항공 / 영상+도로명**을 눌러 실제 사진 표시를 확인합니다. `/api/map/config`의 `imagery_available: true`는 **키가 설정됐다는 뜻**이며 승인·타일 성공을 보장하지 않습니다.

공식 [국토교통부 WMTS/TMS 안내](https://www.data.go.kr/data/3046388/openapi.do)에서 영상·하이브리드·Leaflet 지원 및 무료 표기를 확인했습니다. 사용량은 기관 정책을 따릅니다. 촬영일 미확인 사진은 실시간 영상이나 도로 폭·차량 진입 안전의 증거로 확정하지 않습니다. 연결 방식·오류 대응은 [영상지도 문서](docs/MAP_IMAGERY.md)를 참고하세요.

## 5. 공식 안내 의미 검색: Ollama + BGE-M3 (선택)

외부 유료 LLM 키를 발급받는 과정이 아닙니다. [Ollama 설치](https://ollama.com/download) 후 **로컬 모델 서버**를 실행하고 [공식 BGE-M3 모델](https://ollama.com/library/bge-m3)을 설치합니다. 아래 다운로드는 본인이 의미 검색을 쓰기로 했을 때만 수행합니다.

```powershell
# 실제 연결할 Ollama 서버의 설치 모델 확인
ollama list
# 목록에 없다면 다운로드. Ollama가 다른 컨테이너/서버라면 그 인스턴스에서 준비합니다.
ollama pull bge-m3
```

`.env`에서 다음 항목을 설정합니다. `EMBEDDING_MODEL`은 `ollama list`에 표시되는 정확한 이름과 맞춥니다.

```dotenv
OLLAMA_BASE_URL=http://host.docker.internal:11434
GREENZONE_EMBEDDING_ENABLED=1
EMBEDDING_MODEL=bge-m3:latest
EMBEDDING_OLLAMA_BASE_URL=
EMBEDDING_TIMEOUT_SECONDS=60
# 대화 모델 분류까지 쓸 필요는 없습니다.
GREENZONE_AI_ENABLED=0
```

`EMBEDDING_OLLAMA_BASE_URL`이 비어 있으면 `OLLAMA_BASE_URL`을 재사용합니다. Docker 안의 `localhost`는 호스트 PC가 아니므로 Windows Docker 웹에서는 `host.docker.internal:11434`를 씁니다. Ollama가 다른 포트/컨테이너라면 실제 연결 주소·포트 매핑을 확인하고 개인 `.env`만 맞춥니다. 공유 기본 포트는 **11434**입니다.

```powershell
docker compose up -d --build web
# 이 명령부터 실제 임베딩 모델을 호출하고 DB에 벡터를 저장합니다.
docker compose exec web python -m scripts.index_knowledge --embed
# 검색 문서·현재 모델에 맞는 색인 수 확인. 모델 추론은 하지 않는 상태 조회입니다.
Invoke-RestMethod http://localhost:8000/api/knowledge/status
```

`안내문 등록`만으로 색인이 끝난 것은 아닙니다. `index_complete: true`와 문서/색인 수를 확인하고 도우미의 안내 방식·출처 카드에서 검색 결과를 확인합니다. 문서가 추가되거나 모델/버전이 바뀌면 다시 색인해야 합니다. `index_complete`는 저장 상태이며 실제 검색 품질이나 모델 서버 연결 성공을 뜻하지 않습니다. 키워드 검색으로 돌아가려면 `GREENZONE_EMBEDDING_ENABLED=0`으로 바꾸고 웹을 반영합니다. 상세: [문서 검색 안내](docs/KNOWLEDGE_SEARCH.md).

## 6. 질문 분류 대화 모델도 연결하려면 (선택)

BGE-M3는 임베딩 모델이며 `OLLAMA_MODEL`에 넣는 대화 모델이 아닙니다. `ollama list`에서 **로컬에 설치된 대화 모델**을 확인한 뒤 아래 형식으로 설정합니다.

```dotenv
GREENZONE_AI_ENABLED=1
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_MODEL=설치된_대화모델의_정확한_이름
OLLAMA_TIMEOUT_SECONDS=45
```

실제 모델 이름으로 바꾸고 `docker compose up -d --build web`으로 반영합니다. `/api/ai/status`는 모델 목록 연결을 확인하며 추론 정확도를 검증하지 않습니다. 이 프리뷰는 품목·질문 의도만 모델로 분류하고, 수수료·시간·장소를 모델이 생성해 확정하지 않습니다. 문서 검색과 질문 분류는 별개 스위치입니다. OpenAI·Google Maps·Kakao·Ollama 클라우드 키는 현재 필수가 아니며 해당 클라우드 연결을 구현한 상태도 아닙니다.

## 7. 원본 재수집·추가 분석용 키는 따로 준비

**아래 키를 `.env`에 적는 것만으로 프리뷰가 새 자료를 자동 수집하지 않습니다.** 현재 프리뷰의 `backend`·`scripts`·`compose.yaml`에는 건축HUB/KOSIS/SGIS/도로명주소 수집 연결이 없습니다. 기존 결과를 보는 팀원은 아래 신청을 생략해도 됩니다. 수집·분석 스크립트는 별도 상세 프로젝트가 정본입니다.

| 목적 | 공식 신청/안내 사이트 | 받아야 할 값 → 준비용 변수 | 지금 웹에서 사용? |
| --- | --- | --- | --- |
| 건물 대장 새로 수집 | [국토교통부_건축HUB_건축물대장정보](https://www.data.go.kr/data/15134735/openapi.do) | 해당 서비스 활용 권한이 있는 서비스키 → `BUILDING_API_SERVICE_KEY` | 아니오 |
| 인구·주거 통계 API | [KOSIS 공유서비스](https://kosis.kr/openapi/index/index.jsp) | 공유서비스 인증키 → `KOSIS_API_KEY` | 아니오 |
| 소지역 통계·경계 | [SGIS 개발지원센터](https://sgis.mods.go.kr/developer/html/main.html) | 서비스 ID → `SGIS_CONSUMER_KEY`, 보안 Key → `SGIS_CONSUMER_SECRET` | 아니오 |
| 일반 주소 검색·좌표 제공 | [도로명주소 개발자센터](https://business.juso.go.kr/addrlink/openApi/apiReqst.do) | 검색 승인키 → `JUSO_SEARCH_CONFIRM_KEY`, 좌표 승인키 → `JUSO_COORD_CONFIRM_KEY` | 아니오. 현재 검색은 포함된 건물 파일 내부 조회 |

### 건축HUB: 가입만 하지 말고 서비스 활용신청까지

1. 공공데이터포털 회원가입·로그인 → 위 **건축물대장정보** 서비스 상세 페이지 → 활용신청.
2. 실제 연구·교육 활용 목적을 적고 신청한 서비스의 승인·이용기간을 확인합니다. 포털 키가 있어도 서비스별 활용 권한은 확인해야 합니다.
3. 마이페이지의 신청 내역에서 서비스키를 확인합니다. Encoding/Decoding 표시가 있다면 별도 상세 수집기는 URL 인코딩을 수행하므로 **Decoding 키를 기준으로 준비**합니다. 이 프리뷰에는 수집기가 포함되어 있지 않습니다.
4. 준비할 때만 `.env.example` 하단의 주석 항목을 참고해 **본인 `.env`에** `BUILDING_API_SERVICE_KEY=실제값`을 추가합니다.
5. 상세 페이지의 `OpenAPI활용가이드-_건축HUB_건축물대장_1.0.zip`을 내려받아 표제부 요청 조건·제공 필드·이용 조건을 확인합니다. 키를 넣었다고 건물 좌표·최신 분석이 자동 생성되는 것은 아닙니다.

### KOSIS: 통계 파일이면 API 키 없이, 자동 수집이면 활용신청

1. [국가통계포털](https://kosis.kr/)에서 필요한 통계를 검색하고 지역·기준월·단위를 선택해 CSV/엑셀로 내려받는 방법부터 사용할 수 있습니다.
2. API가 필요하면 KOSIS 공유서비스 로그인 → **OPEN API 인증키 신청/활용신청** → 마이페이지 신청 내역에서 인증키 확인.
3. 준비용 `KOSIS_API_KEY`에 그 인증키를 보관합니다. 공공데이터포털 서비스키·SGIS Secret과 다릅니다.
4. 개발 가이드의 URL 생성에서 통계표·지역·항목·기간을 선택합니다. 생성 URL에는 키가 들어갈 수 있으므로 그대로 공유하지 않습니다.
5. 인구·가구·배출량은 서로 다른 지표입니다. 확보한 통계 파일을 분석에 연결하고 새 결과 파일을 만든 뒤 웹에 반영하는 단계가 필요합니다.

공식 [KOSIS 이용 안내](https://kosis.kr/openapi/community/community_0401List.do)와 [자료·다운로드 통합 TXT](docs/API_KEYS_AND_DATA.txt)를 함께 참고하세요. SGIS·도로명주소는 실제로 그 서비스를 연결하기로 했을 때 신청하고 권한·승인 조건을 추가 확인합니다.

## 8. 설정 변경·종료·문제 해결

```powershell
# .env 또는 소스를 바꾼 뒤 반영. 단순 브라우저 새로고침/컨테이너 restart만으로 환경값이 바뀌지 않습니다.
docker compose up -d --build web
# 실행 상태와 최근 오류
docker compose ps
docker compose logs --tail 50 web
# 종료: DB 볼륨 유지
docker compose down
```

**`docker compose down -v`는 DB 볼륨도 지우므로 사용하지 않습니다.** SQLite DB는 이름 있는 볼륨에 저장됩니다. 기본 웹 실행은 벡터 생성이나 모델 다운로드를 자동 실행하지 않습니다.

| 증상 | 먼저 볼 것 |
| --- | --- |
| Docker 연결 실패 | Docker Desktop 실행·엔진 준비 여부 |
| 8000 포트 사용 중 | `.env`의 `APP_PORT`를 비어 있는 다른 포트로 바꾸고 반영한 뒤 접속 주소도 변경 |
| `.env`를 못 읽음 | 폴더 위치·`.env.txt` 여부·중복 설정·설정 줄 앞 `#` 확인. 터미널에 같은 환경변수가 있으면 파일보다 우선할 수 있음 |
| 관리자 로그인 안 됨 | `ADMIN_USERNAME`·12자 이상 암호·저장 후 컨테이너 반영 여부 |
| 영상 버튼 비활성 | `VWORLD_API_KEY` 빈칸·설명 문구 입력 여부와 웹 반영 여부 |
| 버튼은 켜지지만 사진 실패 | VWorld WMTS/TMS 권한·정확한 등록 URL·유효기간·사용량·인터넷 연결 |
| Ollama 연결 실패 | 11434 서버·Docker/호스트 주소 구분·실제 연결 인스턴스. Ollama는 web과 별도 실행 |
| 안내문 등록 후 색인 미완료 | 임베딩 스위치·모델명·서버 연결·시간 제한 확인. 등록과 벡터 생성은 별개 |
| 새 자료가 검색되지 않음 | 실제 JSON 교체·재빌드 및 문서 변경 시 벡터 재색인 여부. 키 입력만으로 자료가 갱신되지 않음 |

실제 `.env`나 인증 URL 전체를 오류 문의에 첨부하지 말고, 키를 지운 오류 종류·HTTP 상태·설정 이름만 공유합니다.

## 9. Docker 없이 실행 (대안)

Docker 이미지는 Python 3.11 기준입니다. 직접 Python 실행은 `python -m pip install -r backend/requirements.txt` 후 `python run_local.py`를 사용합니다. Ollama 주소는 이때 `http://127.0.0.1:11434`입니다. `START_GREENZONE.bat`도 같은 실행기를 사용합니다. 로컬 실행기의 자동 발급 관리 접속정보는 `storage/local-access.txt`에 보관되며 공유하지 않습니다. Docker DB와 로컬 Python DB는 기본 경로가 다릅니다. 상세: [실행 안내](QUICK_START_KO.md).

## 현재 자료와 화면

- SGIS 2025 공식 행정동 경계, 건축HUB 표제부, VWorld 건물·도로 자료를 공간 조인했습니다.
- 주거·상가·교육·의료·기타·복합용도를 분류합니다. 아파트 주거 배정은 제외하며 자체 계약·실제 이용·발생량은 추가 확인합니다.
- 동 전체에 조사점을 6개씩, 최소 250m 간격으로 배치하고 권역·방문 순서·도로 이동 시나리오를 표시합니다. 실제 일방통행·차종·정차·안전은 확인 전입니다.
- 실제 주소·용도 검색, 지도 확대·이동·내 위치, 제외한 아파트·도로·과거 수거 참고 레이어를 지원합니다.
- 양천구 공식 품목·규격·수수료를 우선 조회합니다. 문서 검색은 BGE-M3 또는 키워드를 사용합니다. 일반·재활용·폐전지 안내를 보강했으며 지역별 범위는 [자료 묶음 안내](docs/DISPOSAL_DATA_HUB.md)에 표시합니다.
- 관리자 DB 수정과 분석 파일 재계산은 별도입니다. 수정한 좌표로 거리 지표를 바꾸려면 분석 결과를 다시 만들어 반영해야 합니다.

일반지도와 기존 분석 파일로 웹 실행 시 외부 자료 키가 필요하지 않습니다. 위성·항공사진과 도로명 겹치기는 `.env`의 `VWORLD_API_KEY`를 사용합니다. 원본 재수집·분석 스크립트와 상세 CSV/보고서는 형제 GreenZone 프로젝트가 정본입니다. 외부 키·관리자 암호는 `.env`에만 보관하며 공유하지 않습니다.

음식물·RFID·영상 AI·실시간 운행·자동단속·치안 연계는 후속 범위입니다. 현재 서비스는 실제 신고·수거 예약·결제를 대신하지 않습니다.

## 더 읽기

- [동 전체 권역·방문 순서 분석](docs/COLLECTION_TERRITORIES.md) · [실제 자료 분석과 한계](docs/REAL_AREA_ANALYSIS.md)
- [품목 DB·ERD](docs/WASTE_DATABASE.md) · [배출 정보 집약체](docs/DISPOSAL_DATA_HUB.md)
- [주소 배정 조회](docs/ADDRESS_TO_TERRITORY.md) · [사용자/관리자 화면](docs/CITIZEN_AND_ADMIN.md)

문서 대조일: 2026-10-19. 공식 서비스 공개 안내와 현재 코드·설정 이름을 대조했습니다. VWorld 로그인 이후 발급 화면·로컬 URL 허용 조건은 이번 점검에서 직접 확인하지 못했으며 신청자가 발급 화면에서 확인해야 합니다.
