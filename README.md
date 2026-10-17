# GreenZone Preview 그린존 시제품

**간략한 5일 팀프로젝트 구현용 저장소**입니다. 양천구의 작은 권역을 대상으로 **후보 위치 분석 → 배치 비교 → 지도·배출 안내 → 담당자 정보 수정**을 연결합니다. 상세 조사·전체 확장 기획의 정본은 별도 GreenZone 프로젝트에서 관리합니다.

> 초기 후보·건물·가구 수·안전 조건은 모두 가상 시연 자료입니다. 지도 배경이 실제여도 표시 지점은 공식 배출장소가 아닙니다.

실제 자료 준비: [직접 작성할 체크리스트 TXT](docs/그린존_직접준비_체크리스트.txt) · [공식 주소·신청 절차·입력 항목 상세](docs/DATA_PREPARATION_CHECKLIST.md)

음식물·RFID·영상 AI·실시간 운행·자동단속·치안 연계는 후속 기획이며 이번 5일 필수 구현에 추가하지 않습니다.

## 이번에 구현한 범위

- 별도 Python/CSV 분석: 안전 조건 제외, 거리·수요·수용 기준에 따른 분산 배정, A/B 비교
- Leaflet 지도와 후보·건물 표시, 배정선, 후보 선정 이유와 보류 사유
- 사용자 `/`와 관리자 `/admin` 화면 분리, 지도 이동·확대 및 내 위치 확인
- 선택한 배치안의 가까운 제안 거점 거리순 목록, 권한 실패 안내와 건물 기준 시연
- 건물 검색과 규칙·출처 안내, 미확인 정보 구분
- 담당자 한 계정 로그인, 후보 위치·상태·메모·규칙 수정과 SQLite 저장
- 수정 충돌 확인과 최근 수정 기록
- 기존 시연 요청 접수·목록
- 선택 AI: 품목·질문 의도 JSON 분류. 위치·시간·링크는 저장된 자료에서 안내

HTML/CSS/JavaScript, FastAPI, Pydantic, SQLite를 사용합니다. React·LangGraph·RAG·영상 분석·새 모델 학습은 추가하지 않았습니다.

## 빠른 실행

Python 환경에 프로젝트 패키지를 준비한 뒤 실행합니다.

```powershell
python -m pip install -r backend/requirements.txt
python run_local.py
```

주소: http://127.0.0.1:8000

관리자 주소: http://127.0.0.1:8000/admin · [화면별 사용법](docs/CITIZEN_AND_ADMIN.md)

Windows에서는 START_GREENZONE.bat를 실행해도 됩니다. 관리자 암호를 따로 설정하지 않았다면 실행기가 임의 암호를 만들고 **storage/local-access.txt**에 접속정보를 기록합니다. 이 파일은 Git에서 제외되며 공유하면 안 됩니다.

화면만 볼 때에는 preview/index.html을 열 수 있습니다. 이 경우 독립 시연 자료를 사용하며 서버 수정·DB 저장은 사용할 수 없습니다.

## 분석을 별도로 진행

```powershell
python scripts/analyze_locations.py
```

data/sample_candidates.csv와 sample_buildings.csv를 읽어 data/analysis_result.json과 비교 CSV를 만듭니다. 웹 분석과 CLI는 같은 계산 함수를 사용합니다. 실제 자료 교체·별도 DB 시작은 [구현 안내](docs/IMPLEMENTATION_GUIDE.md)를 따릅니다.

## AI와 Docker는 선택

기본은 GREENZONE_AI_ENABLED=0이며 모델 호출 없이 동작합니다. AI를 쓰려면 .env의 서버 주소·실제 포트·설치 모델 이름을 함께 설정합니다. 자동 설치·모델 다운로드는 수행하지 않습니다.

Docker는 .env.example을 참고해 준비한 뒤 docker compose up -d --build로 실행합니다. 관리 기능을 쓰려면 ADMIN_PASSWORD를 12자 이상으로 설정합니다. 기본 지도는 별도 유료 지도 키를 사용하지 않습니다.

## 문서

- [구현 범위](docs/IMPLEMENTATION_SCOPE.md)
- [실행과 실제 자료 교체](docs/IMPLEMENTATION_GUIDE.md)
- [구조](docs/ARCHITECTURE.md)
- [API](docs/API_CONTRACT.md)
- [5일 역할 분담](docs/5DAY_SPRINT.md)
- [데이터](data/README.md)

이번 변경에서 pytest 추가·실행과 실제 모델 호출은 수행하지 않습니다. 기존 tests/는 이전 API 골격용 테스트이며, 실행·화면·관리 기능의 검증 범위는 작업 기록과 구분해야 합니다.
