# 구현한 범위와 자료 교체 방법

## 배운 기술을 연결한 범위

| 작업 | 구현 위치 | 배울 내용 |
| --- | --- | --- |
| 안전 조건·거리·분산 배정 | backend/analysis.py | 함수, 조건 분기, 정렬, 거리 계산 |
| CSV를 분석 결과로 변환 | scripts/analyze_locations.py | CSV/JSON 입출력, 자료 검증 |
| 후보·건물·규칙 저장 | backend/catalog.py | CREATE/ALTER/INSERT/SELECT, 기존 자료 보존 |
| 조회·배정·관리 API | backend/app.py | FastAPI, Pydantic, HTTP 상태 코드 |
| 담당자 로그인 | backend/auth.py | 환경변수, 서버 세션, 만료·로그아웃 |
| 사용자 지도·배치 비교·내 위치 | preview/app.js | DOM, fetch, 위치 권한, 거리 계산 |
| 관리자 로그인·정보 수정 | preview/admin.js | 세션, 저장, 수정 충돌과 이력 |
| 공통 화면·서버 통신 | preview/common.js | DOM, fetch, 오류 처리 |
| 선택 AI 분류 | backend/chat_service.py | Ollama JSON 응답, 허용값 검증, 대체 응답 |

## 로컬 실행

먼저 프로젝트 패키지를 사용할 수 있는 Python 환경을 준비한다.

```powershell
python -m pip install -r backend/requirements.txt
python run_local.py
```

Windows에서는 START_GREENZONE.bat로 같은 명령을 실행할 수 있다. 주소는 기본 http://127.0.0.1:8000 이다. 다른 포트는 `python run_local.py --port 8778`처럼 지정한다.

관리자 암호를 별도로 설정하지 않았다면 실행기가 임의 암호를 만들어 storage/local-access.txt에 기록한다. 정보 관리 화면에서 그 접속정보로 로그인한다. 이 파일은 storage 아래의 실행 자료이므로 Git에서 제외된다. 실행을 종료하고 다시 실행하면 자동 발급 암호는 바뀐다.

고정 암호를 원하면 .env.example을 .env로 복사해 ADMIN_PASSWORD를 12자 이상으로 설정한다. .env와 접속정보는 팀 공개 자료에 넣지 않는다.

화면만 확인하려면 preview/index.html을 열 수 있다. 이때는 독립 시연 데이터와 세션 요청만 사용하고 담당자 수정·DB 저장은 사용할 수 없다. 일반 지도는 외부 Leaflet/OSM 로딩이 필요하며 연결 실패 시 같은 좌표의 도식을 보여 준다.

## 실제 자료를 넣는 순서

1. data/sample_candidates.csv와 sample_buildings.csv의 열 구성을 참고해 별도 실제 자료 파일을 작성한다. 기존 샘플은 가상 자료다.
2. 좌표·수요·단위를 확인한다. 안전 상태는 pass/fail/unknown이다. 미확인을 pass로 채우지 않는다.
3. 실제 자료에는 is_demo=0, source_id, checked_at을 적고 메타정보 sources에 원문을 등록한다. source_id는 수치의 실제 근거를 가리켜야 한다.
4. 같은 단위의 수요·수용 기준을 사용한다. 예를 들어 가구 수와 쓰레기 무게를 같은 숫자로 비교하지 않는다.
5. 메타정보의 study_area와 analysis_settings를 실제 분석 권역·후보 조합으로 맞춘다. 행정경계와 프로젝트 분석 범위를 구분한다.
6. 별도 파일로 분석 결과를 만든다.

```powershell
python scripts/analyze_locations.py --candidates data/my_candidates.csv --buildings data/my_buildings.csv --metadata data/my_metadata.json --out data/my_result.json
```

7. .env에서 GREENZONE_CATALOG_PATH를 결과 파일로 지정하고, DEMO_DB_PATH는 별도의 새 DB 경로로 지정해 실행한다. 기존 DB는 덮어쓰지 않는다.

```text
GREENZONE_CATALOG_PATH=data/my_result.json
DEMO_DB_PATH=storage/my_pilot.db
```

초기 JSON은 비어 있는 DB를 채우는 자료다. 파일만 바꿔도 기존 DB의 담당자 수정 사항을 자동으로 덮어쓰지 않는다. 이미 입력한 후보·규칙은 정보 관리 화면에서 수정한다.

## 분석의 의미

- A안은 지정한 소수 후보, B안은 지정한 분산 후보 조합을 비교한다. 후보 조합은 메타정보에서 지정한다.
- 안전 부적합·미확인·보류 후보는 배정하지 않는다.
- 큰 수요의 건물부터 거리와 현재 담당 부담을 함께 보며 순차 배정한다.
- 거리 상한과 수용 기준을 충족하지 못한 건물은 사유와 함께 미배정으로 남긴다.
- 거리 상한·부하 가중치·수용 수치는 프로젝트 가정이며 법정 기준이 아니다.
- 결과는 직선거리 기반 탐색안이다. 실제 보행경로·수거차량 운행·배출량·안전 개선 효과를 증명하지 않는다.

## 지도와 안내

Leaflet 공식 예제와 OSM 타일 정책에 맞춰 배경지도를 요청하고 출처를 표시한다. 대량 다운로드·사전 저장 기능은 없다.

- https://leafletjs.com/examples/quick-start/
- https://operations.osmfoundation.org/policies/tiles/

가상 수치는 지도 배경이 실제여도 가상으로 표시한다. 실제 자료도 현재는 배치 제안이며, 기관·주민·부지 확인 없이 실제 배출장소나 주차금지구역으로 승인하지 않는다. `/api/match`의 matched_point는 실제 운영 승인 기능을 구현하기 전까지 null이다.

## AI를 선택적으로 연결

기본은 GREENZONE_AI_ENABLED=0이며, 모델 호출 없이 키워드·저장된 규칙으로 안내한다. 실제 모델을 사용하려면 .env의 서버 주소와 설치 모델 이름을 직접 설정한다. 서버·모델은 자동 설치하거나 다운로드하지 않는다.

```text
GREENZONE_AI_ENABLED=1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_MODEL=사용할_모델의_정확한_이름
```

Docker에서 호스트 모델에 접근할 때는 주소를 host.docker.internal과 실제 포트로 맞춘다. API는 모델의 category/topic 허용값만 사용하고 답변 문장은 DB에서 만든다. 형식이 틀리거나 모델이 중단되면 기본 규칙 안내를 사용한다. 정규식·공간 배정 알고리즘을 학습한 AI라고 설명하지 않는다.

## 작은 시제품의 운영 조건

담당자 한 계정과 단일 서버 프로세스를 전제로 한다. 수정은 세션 인증 후 저장하며, 다른 수정과 충돌하면 다시 불러오도록 안내한다. 실제 다중 담당자·다중 서버·대외 서비스 운영은 별도 설계 대상이다.

## 이번 작업의 확인 범위

CSV 기반 시연 분석 결과와 코드 구문 확인을 구분해 기록한다. 현재 요청에 따라 테스트 파일 추가·pytest 실행·모델 호출은 수행하지 않는다. 실행 확인 여부는 작업 마무리 시 별도로 명시한다.
