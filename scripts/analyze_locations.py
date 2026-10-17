"""별도 분석 작업: CSV 입력을 정리해 웹이 읽을 JSON과 비교 CSV를 만든다."""
from pathlib import Path
import argparse
import csv
import json
import sys
import math

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.analysis import compare_plans


def rows(path: Path, numeric: tuple[str, ...]) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        result = list(csv.DictReader(f))
    for row in result:
        for key in numeric:
            value = row.get(key, "").strip()
            row[key] = float(value) if value else None
            if row[key] is not None and not math.isfinite(row[key]):
                raise ValueError(f"{key}에 유한한 숫자를 입력해 주세요.")
        row["is_demo"] = str(row.get("is_demo", "1")).lower() in ("1", "true", "yes")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", type=Path, default=ROOT / "data/sample_candidates.csv")
    parser.add_argument("--buildings", type=Path, default=ROOT / "data/sample_buildings.csv")
    parser.add_argument("--metadata", type=Path, default=ROOT / "data/catalog_metadata.json")
    parser.add_argument("--out", type=Path, default=ROOT / "data/analysis_result.json")
    parser.add_argument("--preview-snapshot", action="store_true", help="명시적으로 독립 프리뷰용 JS도 작성")
    args = parser.parse_args()
    catalog = json.loads(args.metadata.read_text(encoding="utf-8"))
    catalog["candidates"] = rows(args.candidates, ("lat", "lon", "capacity"))
    catalog["buildings"] = rows(args.buildings, ("lat", "lon", "demand"))
    for building in catalog["buildings"]:
        building.setdefault("verification_status", "unverified")
    source_ids = {s["source_id"] for s in catalog.get("sources", [])}
    for key, id_field in (("candidates", "candidate_id"), ("buildings", "building_id")):
        ids = [r[id_field] for r in catalog[key]]
        if len(ids) != len(set(ids)):
            raise ValueError(f"{key}의 ID가 중복되었습니다.")
        for r in catalog[key]:
            if r["lat"] is not None and not -90 <= r["lat"] <= 90:
                raise ValueError("위도 범위를 확인해 주세요.")
            if r["lon"] is not None and not -180 <= r["lon"] <= 180:
                raise ValueError("경도 범위를 확인해 주세요.")
            if not r["is_demo"] and (not r.get("source_id") or not r.get("checked_at")):
                raise ValueError("실제 후보·건물에는 출처 ID와 확인일이 필요합니다.")
            if r.get("source_id") and r["source_id"] not in source_ids:
                raise ValueError("메타정보에 등록되지 않은 출처 ID입니다.")
            if key == "candidates":
                for field in ("truck_access", "stopping_space", "work_space", "pedestrian_clear"):
                    if r.get(field) not in ("pass", "fail", "unknown"):
                        raise ValueError("안전 조건은 pass/fail/unknown 중 하나로 입력해 주세요.")
                if r.get("review_status") not in ("review", "selected", "hold", "excluded"):
                    raise ValueError("후보 검토 상태를 확인해 주세요.")
    catalog["analysis"] = compare_plans(catalog["buildings"], catalog["candidates"], catalog.get("analysis_settings"))
    from backend.analysis import eligibility
    for candidate in catalog["candidates"]:
        candidate["eligibility"] = eligibility(candidate)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(catalog, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.preview_snapshot:
        (ROOT / "preview/demo-data.js").write_text("'use strict';\nwindow.GREENZONE_DEMO = " + json.dumps(catalog, ensure_ascii=False) + ";\n", encoding="utf-8")
    with args.out.with_suffix(".comparison.csv").open("w", encoding="utf-8-sig", newline="") as f:
        fields = ["plan_id", "candidate_count", "assigned_buildings", "unassigned_buildings", "average_distance_m", "max_distance_m", "coverage_pct"]
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for plan in catalog["analysis"]["plans"]:
            w.writerow({"plan_id": plan["plan_id"], **{k: plan["metrics"][k] for k in fields[1:]}})
    print(f"분석 결과: {args.out}")
    print("안전 미확인 후보는 보류하며, 거리는 직선거리 참고값입니다.")


if __name__ == "__main__":
    main()
