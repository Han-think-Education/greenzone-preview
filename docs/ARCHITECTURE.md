# GreenZone Preview 구성

```text
Windows host
  Ollama :11435   ← 모델 서버는 Windows 설치본 유지
     ↑ HTTP /api/chat, /api/tags
Docker (WSL2 / Docker Desktop)
  FastAPI :8000   ← host.docker.internal:11435
     ↕
  SQLite volume
     ↑
브라우저 JS fetch + SVG 데모 지도
```

## API → DB → LLM 경계

- GET `/api/zones` / `/api/buildings` / `/api/disposal-rules`는 SQLite와 기본 정적 규칙을 조회한다.
- POST `/api/match`는 검증 전 데이터를 실제 배출 위치로 추천하지 않는다.
- POST `/api/requests`는 DB에 시연 요청만 저장하며 실제 예약은 생성하지 않는다.
- POST `/api/chat`는 Python으로 입력 품목을 검증한 뒤 Ollama에 안전한 안내문을 기반으로 응답하도록 요청한다.
- Ollama 오류 시 fallback이며 `ai_used=false`로 표기한다.
- **LangGraph는 후속 단계**에서 상태 그래프와 분기 노드로 연결할 예정이다. 현재 프리뷰의 그래프는 설계 시각화이다.

## Docker 네트워킹

- `.env.example`: `OLLAMA_BASE_URL=http://host.docker.internal:11435`
- 컨테이너 안의 `localhost`는 Windows 호스트가 아니다.
- Docker Desktop의 `host.docker.internal` 경로를 우선 사용한다. 독립 WSL Docker Engine이면 호스트 접근 및 라우팅을 별도 확인한다.
- Ollama를 인터넷에 공개하지 않는다.
