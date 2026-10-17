"""기능 연결을 위한 명시적인 가상 데이터. 현장·공식 자료가 아니다."""
from pathlib import Path
import csv
import json

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)

candidate_fields = ["candidate_id", "name", "lat", "lon", "capacity", "capacity_unit", "truck_access", "stopping_space", "work_space", "pedestrian_clear", "review_status", "rationale", "safety_note", "source_id", "checked_at", "is_demo"]
candidates = []
for cid, name, lat, lon, note in [
    ("GZ-01", "시연 후보 01 · 북서", 37.5234, 126.8676, "북서측 가상 건물을 나누어 담당하는 배치 가정"),
    ("GZ-02", "시연 후보 02 · 북동", 37.5231, 126.8746, "북동측 가상 건물의 접근 부담을 줄이는 배치 가정"),
    ("GZ-03", "시연 후보 03 · 남측", 37.5189, 126.8710, "남측 건물을 분산시켜 먼 거리 배정을 줄이는 배치 가정"),
    ("GZ-04", "시연 후보 04 · 보류", 37.5212, 126.8704, "가까워도 보행 안전이 충족되지 않으면 제외하는 시연"),
]:
    candidates.append(dict(zip(candidate_fields, [cid, name, lat, lon, 65, "시연 가구", "pass", "pass", "pass", "fail" if cid == "GZ-04" else "pass", "hold" if cid == "GZ-04" else "review", note, "위치와 안전 조건 모두 가상입니다. 현장 확인 전 실제 배출 금지.", "DEMO", "2026-10-17", 1])))

point_coords = {"A": [(107,120),(165,116),(221,124),(292,115),(353,130),(124,171),(207,174),(312,176)], "B": [(525,125),(587,121),(654,130),(715,119),(774,144),(542,176),(632,172),(753,178)], "C": [(161,356),(229,355),(309,358),(490,345),(553,373),(632,400),(259,407),(412,412)]}
building_fields = ["building_id", "zone_id", "building_name", "road_address", "lat", "lon", "demand", "demand_unit", "verification_status", "source_id", "checked_at", "is_demo"]
buildings = []
for zone, points in point_coords.items():
    for i, (x, y) in enumerate(points, 1):
        lat = round(37.525 - y / 490 * 0.008, 6)
        lon = round(126.865 + x / 880 * 0.012, 6)
        buildings.append(dict(zip(building_fields, [f"{zone}-{i:02d}", zone, f"데모 빌라 {zone}-{i:02d}", f"ZONE-{zone} 시연용 가상 주소", lat, lon, 4 + i % 5, "시연 가구", "unverified", "DEMO", "2026-10-17", 1])))

for filename, fields, records in [("sample_candidates.csv", candidate_fields, candidates), ("sample_buildings.csv", building_fields, buildings)]:
    with (OUT / filename).open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)

metadata = {
    "study_area": {"name": "양천구 지도 배경 위 시연 권역", "description": "행정경계와 실제 배출구역이 아닙니다. 모든 후보·건물 위치는 가상입니다.", "center": [37.521, 126.871], "bounds": [[37.517, 126.865], [37.525, 126.877]], "is_demo": True},
    "analysis_settings": {"plan_a_ids": ["GZ-01", "GZ-02"], "plan_b_ids": ["GZ-01", "GZ-02", "GZ-03"], "max_distance_m": 600, "balance_m": 120},
    "sources": [
        {"source_id": "DEMO", "title": "시연용 가정 자료", "url": None, "reference_date": "2026-10-17", "note": "가상 좌표·가구 수·수용 기준·안전 상태. 실제 위치 선정 근거가 아닙니다."},
        {"source_id": "ROUTE2020", "title": "2020 양천구 음식물 수거표", "url": "https://data.seoul.go.kr/dataList/OA-22090/F/1/datasetView.do", "reference_date": "2020-09-29", "note": "추가 조사 참고 출처. 현재 GPS·정차점을 뜻하지 않으며 시연 수치의 근거가 아닙니다."},
        {"source_id": "NOTICE", "title": "양천구 공지 자료", "url": "https://data.yangcheon.go.kr/openinf/sheetview.jsp?infId=OA-12718&tMenu=11", "reference_date": None, "note": "현행 폐기물 공지를 선별해야 하는 조사 출처. 개별 규칙은 아직 미확인."},
    ],
    "rules": [
        {"rule_id": f"RULE-{category}", "category": category, "days": "", "time_text": "", "guidance": guide, "source_id": "DEMO", "source_url": "https://smartclean.yangcheon.go.kr/" if category == "bulky" else "", "reference_date": "", "verification_status": "unverified", "is_demo": True}
        for category, guide in [
            ("general", "일반 생활폐기물의 현행 배출 위치·요일은 공식 자료 확인이 필요합니다."),
            ("recycle", "재활용품은 품목별 분리배출 기준과 해당 건물의 배출 위치를 확인해 주세요."),
            ("battery", "검증된 폐건전지 전용 수거함이 아직 등록되지 않았습니다."),
            ("bulky", "대형폐기물은 양천구 공식 신고 절차를 확인해 주세요. 이 웹은 실제 신청을 대신하지 않습니다."),
        ]
    ],
}
(OUT / "catalog_metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
print("가상 CSV와 출처 메타정보를 준비했습니다. 실제 데이터가 아닙니다.")
