# 현재 실행 자료

- `pilot_analysis.json`: 신월1동·화곡1동의 공식 자료 공간 조인·비교 결과. 경계·필지·도로·현장 조사 기준점.
- `analysis_result.json`: 실제 대상 필지와 조사 기준점을 SQLite에 등록하는 카탈로그. 기준점 안전 상태는 unknown, 수용량은 null.
- `waste_catalog.json`: 양천구 공식 대형폐기물 품목명 91개·규격별 수수료 268건.
- `waste_schema.sql`: 품목 검색 추가 테이블.
- `knowledge_documents.json`: 양천구·강서구·전국 공통의 확보된 공식 안내를 요약한 19개 문단.

기존 가상 CSV·가상 메타정보·데모 지도 스냅샷은 제거했습니다. 복구용 보관본은 상세 프로젝트 `GreenZone/research/retired_demo_20261018`에 있습니다.

[실제 지역 분석 설명](../docs/REAL_AREA_ANALYSIS.md) · [품목 DB 설명](../docs/WASTE_DATABASE.md).

동 전체 권역·기준점 개수·거리 계산은 분석 매개변수이며 실제 배출 장소 지정·작업 안전·보행 거리·수거 시간 개선을 입증한 결과가 아닙니다.
