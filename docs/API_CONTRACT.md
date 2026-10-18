> 2026-10-18 갱신: 가상 지도·A/B 시연은 제거하고 실제 두 지역 분석으로 교체했습니다. 현재 지도·자료·한계는 [실제 지역 분석](REAL_AREA_ANALYSIS.md)을 먼저 읽으세요. 아래 이전 구현 기록의 시연 화면·샘플 실행은 현재 흐름과 다를 수 있습니다.

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
| GET | /api/knowledge/status | 문서 수·벡터 색인 수·임베딩 설정 여부. 모델 연결 호출 없음 |
| GET | /api/auth/session | 로그인 여부 |
| POST | /api/auth/login | 담당자 로그인 |
| POST | /api/auth/logout | 로그아웃 |
| PATCH | /api/admin/candidates/{candidate_id} | 후보 위치·조건·메모 수정 |
| PATCH | /api/admin/rules/{rule_id} | 규칙·출처·기준일 수정 |
| GET | /api/admin/history | 최근 수정 기록 |

수정 요청에는 현재 revision이 필요합니다. 인증 실패 401, 원본 없음 404, 수정 충돌 409, 입력 오류 422로 응답합니다. 후보의 is_demo와 운영 승인 여부는 이 수정 API로 바꿀 수 없습니다.

match 응답의 proposed_candidate는 프로젝트 배치 제안이며 실제 운영 장소가 아닙니다. matched_point는 null을 유지합니다.

AI 응답의 ai_used는 실제 분류 결과가 허용 형식으로 사용된 경우에만 true입니다. 기본은 AI 비활성 상태이며 모델 호출을 하지 않습니다.

2026-10-18 추가: chat 입력은 `district_code`(기본 11470)와 선택 `dong`을 받습니다. 공식 안내 요약이 검색되면 `citations`에 제목·본문·원문 URL·확인일·기준일·시행기간을 반환합니다. `retrieval.mode`는 embedding / keyword / no_documents / out_of_scope이며, `retrieval.embedding_used`로 실제 임베딩 사용 여부를 구분합니다. `ai_used`는 기존 생성 모델 분류 여부를 유지하며 임베딩 사용을 뜻하지 않습니다. 답변 생성은 하지 않습니다. 현재 검색 문서는 양천구 대형폐기물 안내이며, 결과가 없으면 기존 안내·질문 재확인을 사용합니다. `is_demo`는 지도 등 서비스의 시연 상태를 유지하며, 요약의 `source_checked`는 원문 확인 상태이지 배출장소 승인 상태가 아닙니다.

## multi_use_v2 / 자료 집약체 보강

- GET /api/pilot-analysis: 별도 계산한 전체 용도 필지·주변 맥락·직선거리 시나리오.
- GET /api/data-hub/status: 자료 묶음 수량과 미완료 범위. 모델 호출 없음.
- POST /api/chat: 선택 context={district_code,item_id,pending:item|specification}. 응답 context와 suggestions=[{label,message}]로 품목/규격 확인. 지역 변경 시 폐기. DB의 활성 품목·지역·규격을 다시 검증.
- 공식 문서 19개는 양천구/강서구/전국 공통 및 질문유형별로 필터링. 수수료는 양천구만 제공.
- item_clarification/facility_clarification은 추가 정보 요청. item_database는 정확 조회. needs_local_data는 해당 지역 근거 부족.

## district_corridors_v3

`GET /api/pilot-analysis` 응답은 analysis_version, parameters 및 각 동의 service_sectors(GeoJSON), collection_route(order/legs/내부 이동 비교), survey_references(권역/방문 번호), survey_assignments(도로 접근 대용거리)를 포함한다. 이전 block 필드는 사용하지 않고 과거 지표는 legacy_block_summary로 보관한다.

현재 후보 API와 카탈로그는 analysis_active=1만 반환한다. 이전 실제 조사점은 보존하며 archived_candidate_count에 수량을 표시한다. 지도 분석은 별도 파일이므로 관리자 좌표 수정이 분석 경로에 자동 반영되지 않는다.

## 0.7.0 영상지도

- `GET /api/map/config`: 영상 키 설정 유무, 공급자, 최대 배율, 촬영일 미확인 상태를 반환. 인증키·등록 URL은 반환하지 않는다. 실제 연결 성공 여부와 별개이다.
- `GET /api/map/tiles/{layer}/{z}/{x}/{y}`: layer는 Satellite 또는 Hybrid, z는 1~19. 서버에서 VWorld를 호출하여 JPEG/PNG만 반환한다. 키 누락 503, 공급자 오류 502, 타일 인덱스 범위 초과 404. 오류 응답에 공급자 원문·인증 URL을 넣지 않는다.
- 영상 배경 전환은 분석 결과·운영 승인 상태를 바꾸지 않는다. `basemap=street|satellite|hybrid`로 초기 배경을 지정할 수 있다.
