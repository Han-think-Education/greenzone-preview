# GreenZone Preview | 그린존 프리뷰

**5일 교육 프로젝트**: Windows/WSL Docker + Windows Ollama(11435) + FastAPI + SQLite + HTML/JS.

> ⚠ ZONE A/B/C, 건물 24개, 지도 마커는 **전부 가상 시연 데이터**입니다. 실제 배출 장소, 행정 정보, 예약 서비스가 아닙니다.

## 지금 작동하는 부분

- 지도 시뮬레이션: 3개 구역, 가상 건물 24개, 선택 및 검색
- 배출 분류와 규칙 조회, 수량 검증, 시연 요청 등록, SQLite 저장
- FastAPI GET / POST / JSON, 자동 Swagger 문서
- Windows Ollama **11435** 연결: `http://host.docker.internal:11435` (Docker 컨테이너에서)
- Ollama 미접속 시 안전한 규칙 기반 안내로 전환, **AI 연결 여부를 화면에서 구분**
- **LangGraph 미구현**: 도식 화면은 개발 예정 기능 설명입니다.
- **실제 카카오 지도 미연동**: 현재는 클릭 가능한 SVG 지도 도식입니다.

## 빠른 실행

```powershell
# Windows PowerShell에서 프로젝트 폴더 열기
Invoke-RestMethod http://127.0.0.1:11435/api/tags
Copy-Item .env.example .env
notepad .env
# .env의 OLLAMA_MODEL을 설치된 모델 이름으로 수정
docker compose up -d --build
```

URL: http://127.0.0.1:8000 / API: http://127.0.0.1:8000/docs / AI 상태: http://127.0.0.1:8000/api/ai/status

**Ollama는 중복 설치하지 않습니다.** Docker는 FastAPI 웹 서버만 구동합니다.

자세한 확인 및 연결 문제 해결: [`QUICK_START_KO.md`](QUICK_START_KO.md).

## 구성

```text
preview/                    HTML/CSS/JS 프리뷰, 시연 지도
backend/app.py               FastAPI + SQLite + 규칙 매칭
backend/chat_service.py      Windows Ollama API 호출
compose.yaml                 Docker 웹 서버만 구동
compose.container-ollama.yaml 선택적으로 Ollama 컨테이너 사용
.env.example                 사용자 로컬 환경 설정 예제
.github/workflows/tests.yml  pytest CI
tests/                       API 11개 테스트
```

## GitHub

교육용 저장소: https://github.com/Han-think-Education/greenzone-preview

저장소는 Public입니다. 실제 `.env`는 Git에서 제외됩니다. 최초 push는 [`docs/GITHUB_SETUP.md`](docs/GITHUB_SETUP.md) 참고.
