# API 계약 v0.4

| 방식 | 경로 | 동작 |
| --- | --- | --- |
| GET | /health | 기본 서비스 상태 |
| GET | /api/config | 관리 설정·선택 AI 활성 여부 |
| GET | /api/catalog | 후보·건물·규칙·출처·분석 결과 |
| GET | /api/candidates | 검토 상태와 선정 근거 |
| GET | /api/analysis | A/B 배정·부담·직선거리 비교 |
| GET | /api/zones | 기존 시연 권역 |
| GET | /api/buildings | 기존 건물 검색 대상 |
| GET | /api/disposal-rules | 저장된 품목별 규칙 |
| POST | /api/match | building_id·category·quantity·plan_id로 제안 배정과 안내 조회 |
| GET / POST | /api/requests | 기존 시연 요청 조회·저장 |
| POST | /api/chat | 품목·질문 의도와 저장된 규칙 안내 |
| GET | /api/ai/status | 선택 AI 상태 |
| GET | /api/auth/session | 로그인 여부 |
| POST | /api/auth/login | 담당자 로그인 |
| POST | /api/auth/logout | 로그아웃 |
| PATCH | /api/admin/candidates/{candidate_id} | 후보 위치·조건·메모 수정 |
| PATCH | /api/admin/rules/{rule_id} | 규칙·출처·기준일 수정 |
| GET | /api/admin/history | 최근 수정 기록 |

수정 요청에는 현재 revision이 필요합니다. 인증 실패 401, 원본 없음 404, 수정 충돌 409, 입력 오류 422로 응답합니다. 후보의 is_demo와 운영 승인 여부는 이 수정 API로 바꿀 수 없습니다.

match 응답의 proposed_candidate는 프로젝트 배치 제안이며 실제 운영 장소가 아닙니다. matched_point는 null을 유지합니다.

AI 응답의 ai_used는 실제 분류 결과가 허용 형식으로 사용된 경우에만 true입니다. 기본은 AI 비활성 상태이며 모델 호출을 하지 않습니다.
