# FastAPI API 계약 / 프리뷰 v0.2

| Method | Path | 동작 |
| --- | --- | --- |
| GET | `/health` | FastAPI 상태 확인 (Ollama와 무관) |
| GET | `/api/zones` | 3개 가상 ZONE 정보 |
| GET | `/api/buildings?zone=A` | 구역별 가상 건축물 조회 |
| GET | `/api/buildings/{building_id}` | 건축물 상세 (없으면 404) |
| GET | `/api/disposal-rules` | 품목별 검증 상태 |
| POST | `/api/match` | `{building_id, category, quantity}` → 규칙 기반 결과 |
| GET | `/api/requests` | SQLite 요청 목록 |
| POST | `/api/requests` | SQLite 시연 요청 등록, 실제 예약 X |
| GET | `/api/ai/status` | Ollama 연결 및 모델 다운로드 상태 |
| POST | `/api/chat` | `{message}` → `category`, `mode`, `ai_used`, `response` |

## Ollama AI 응답 `mode`

- `ollama`: 실제 Ollama `/api/chat` 호출 성공.
- `fallback`: Ollama 호출 실패 → 기본 규칙으로 처리 (AI 사용이라고 표기하지 않음).
- `needs_clarification`: 품목 불명확 → 사용자에게 재질문 (일반쓰레기로 강제 분류하지 않음).

**모든 샘플 건물·거점·배출 위치는 검증 전입니다.**
