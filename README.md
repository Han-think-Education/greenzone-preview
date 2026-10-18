# GreenZone Preview

5일 팀프로젝트용 웹 시제품. **신월1동·화곡1동 공식 자료 분석 → 동 전체 권역 지도 → 도로 방문 순서 비교 → 배출 안내**를 연결합니다.

기존 가상 지도·A/B 배치 시연은 2026-10-18 제거했습니다. 주황색은 실제 도로 선형을 바탕으로 한 현장 조사 기준점이며 배출·정차 장소가 아닙니다.

## 바로 보기

- **팀원 공유:** [3쪽 화면 가이드 PDF](output/pdf/그린존_프리뷰_팀원_화면가이드.pdf) · [캡처와 설명](docs/TEAM_PREVIEW_GUIDE.md) · [Docker 실행 순서](QUICK_START_KO.md)
- [주소·건물명에서 담당 제안 권역 찾기](docs/ADDRESS_TO_TERRITORY.md)
- [일반지도·위성/항공사진·영상+도로명 전환](docs/MAP_IMAGERY.md)
- [최신: 동 전체 권역 분산·도로 방문 순서](docs/COLLECTION_TERRITORIES.md)

- [배출 정보 집약체·상가/학교 포함·품목 되묻기](docs/DISPOSAL_DATA_HUB.md)

- [실제 두 지역 분석·수치·방법·한계](docs/REAL_AREA_ANALYSIS.md)
- [양천구 품목 DB·ERD](docs/WASTE_DATABASE.md): 품목명 91개·규격별 수수료 268건
- [공식 안내 문서 검색](docs/KNOWLEDGE_SEARCH.md)
- [실행 안내](QUICK_START_KO.md) · [API 키 준비](docs/API_KEYS_AND_DATA.txt)

## 실행

```powershell
docker compose up -d --build web
```

지도: http://localhost:8000/ · 도우미: http://localhost:8000/#assistant · 관리자: http://localhost:8000/admin

Python 실행은 `python -m pip install -r backend/requirements.txt` 후 `python run_local.py`를 사용합니다. 포트는 APP_PORT 설정을 따릅니다. HTML 파일을 직접 여는 방식의 가상 시연은 제거했으며 서버로 접속합니다.

## 현재 자료와 화면

- SGIS 2025 공식 행정동 경계, 건축HUB 표제부, VWorld 건물·도로 자료를 공간 조인했습니다.
- 주거·상가·교육·의료·기타·복합용도를 분류합니다. 아파트 주거 배정은 제외하며 자체 계약·실제 이용·발생량은 추가 확인합니다.
- 동 전체에 조사점을 6개씩, 최소 250m 간격으로 배치하고 권역·방문 순서·도로 이동 시나리오를 표시합니다. 실제 일방통행·차종·정차·안전은 확인 전입니다.
- 실제 주소·용도 검색, 지도 확대·이동·내 위치, 제외한 아파트·도로·과거 수거 참고 레이어를 지원합니다.
- 양천구 공식 품목·규격·수수료를 우선 조회합니다. 문서 검색은 BGE-M3 또는 키워드를 사용합니다. 일반·재활용·폐전지 안내를 보강했으며 지역별 범위는 [자료 묶음 안내](docs/DISPOSAL_DATA_HUB.md)에 표시합니다.
- 관리자 DB 수정과 분석 파일 재계산은 별도입니다. 수정한 좌표로 거리 지표를 바꾸려면 분석 결과를 다시 만들어 반영해야 합니다.

일반지도와 기존 분석 파일로 웹 실행 시 외부 자료 키가 필요하지 않습니다. 위성·항공사진과 도로명 겹치기는 `.env`의 `VWORLD_API_KEY`를 사용합니다. 원본 재수집·분석 스크립트와 상세 CSV/보고서는 형제 GreenZone 프로젝트가 정본입니다. 외부 키·관리자 암호는 `.env`에만 보관하며 공유하지 않습니다.

음식물·RFID·영상 AI·실시간 운행·자동단속·치안 연계는 후속 범위입니다. 현재 서비스는 실제 신고·수거 예약·결제를 대신하지 않습니다.
