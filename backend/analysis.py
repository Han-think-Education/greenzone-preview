"""CSV 분석과 웹에서 함께 쓰는 작은 공간 분석 모듈. 외부 패키지 불필요."""
from __future__ import annotations

import math

SAFETY_FIELDS = ("truck_access", "stopping_space", "work_space", "pedestrian_clear")
SAFETY_LABELS = {"truck_access": "차량 진입", "stopping_space": "정차 공간", "work_space": "작업 공간", "pedestrian_clear": "보행 통로"}


def distance_m(a: dict, b: dict) -> float:
    """WGS84 위경도의 직선거리. 보행 경로·수거 차량 동선이 아니다."""
    p1, p2 = math.radians(float(a["lat"])), math.radians(float(b["lat"]))
    dp = p2 - p1
    dl = math.radians(float(b["lon"]) - float(a["lon"]))
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 6371000 * 2 * math.asin(min(1, math.sqrt(h)))


def eligibility(candidate: dict) -> dict:
    reasons = []
    state = candidate.get("review_status", "review")
    if state in ("hold", "excluded"):
        reasons.append("담당자가 보류 또는 제외한 후보")
    for field in SAFETY_FIELDS:
        value = candidate.get(field, "unknown")
        if value != "pass":
            reasons.append(f"{SAFETY_LABELS[field]} {'부적합' if value == 'fail' else '미확인'}")
    if candidate.get("lat") is None or candidate.get("lon") is None:
        reasons.append("위치 좌표 미확인")
    if float(candidate.get("capacity") or 0) <= 0:
        reasons.append("수용 기준 미확인")
    return {"eligible": not reasons, "reasons": reasons,
            "label": "시연 조건 통과" if not reasons and candidate.get("is_demo") else "조건 검토 통과" if not reasons else "배정 보류"}


def make_plan(plan_id: str, label: str, buildings: list[dict], candidates: list[dict], chosen_ids: list[str], max_distance_m: float = 600, balance_m: float = 120) -> dict:
    chosen = [c for c in candidates if c["candidate_id"] in chosen_ids and eligibility(c)["eligible"]]
    loads = {c["candidate_id"]: 0.0 for c in chosen}
    assignments = []
    # 큰 수요부터 배정하는 단순 탐색. 전역 최적화를 주장하지 않는다.
    for building in sorted(buildings, key=lambda b: (-float(b.get("demand") or 0), b["building_id"])):
        demand = building.get("demand")
        base = {"building_id": building["building_id"], "candidate_id": None, "distance_m": None,
                "demand": demand, "distance_method": "straight_line"}
        if demand is None or float(demand) <= 0 or building.get("lat") is None or building.get("lon") is None:
            assignments.append({**base, "reason": "좌표 또는 수요 자료 미확인"})
            continue
        options = []
        for c in chosen:
            cid, capacity = c["candidate_id"], float(c["capacity"])
            dist = distance_m(building, c)
            if loads[cid] + float(demand) <= capacity and dist <= max_distance_m:
                # 거리와 현재 부하를 함께 보되 안전 조건은 위에서 먼저 제외한다.
                score = dist + balance_m * (loads[cid] / capacity)
                options.append((score, dist, cid))
        if not options:
            assignments.append({**base, "reason": "거리 상한 또는 수용 기준을 만족하는 후보 없음"})
            continue
        _, dist, cid = min(options)
        loads[cid] += float(demand)
        assignments.append({**base, "candidate_id": cid, "distance_m": round(dist, 1), "reason": "거리·담당 부담을 고려한 제안 배정"})
    assigned = [a for a in assignments if a["candidate_id"]]
    known_demand = sum(float(b["demand"]) for b in buildings if b.get("demand") is not None)
    assigned_demand = sum(float(a["demand"]) for a in assigned)
    return {"plan_id": plan_id, "label": label, "candidate_ids": [c["candidate_id"] for c in chosen],
            "parameters": {"max_straight_distance_m": max_distance_m, "balance_weight_m": balance_m},
            "assignments": assignments,
            "loads": [{"candidate_id": c["candidate_id"], "demand": loads[c["candidate_id"]],
                       "capacity": float(c["capacity"]), "unit": c.get("capacity_unit", "가구"),
                       "building_count": sum(a["candidate_id"] == c["candidate_id"] for a in assigned)} for c in chosen],
            "metrics": {"candidate_count": len(chosen), "total_buildings": len(buildings),
                        "assigned_buildings": len(assigned), "unassigned_buildings": len(buildings) - len(assigned),
                        "known_demand": known_demand, "assigned_demand": assigned_demand,
                        "coverage_pct": round(assigned_demand / known_demand * 100, 1) if known_demand else None,
                        "average_distance_m": round(sum(a["distance_m"] for a in assigned) / len(assigned), 1) if assigned else None,
                        "max_distance_m": max((a["distance_m"] for a in assigned), default=None)}}


def compare_plans(buildings: list[dict], candidates: list[dict], settings: dict | None = None) -> dict:
    settings = settings or {}
    units = {b.get("demand_unit", "가구") for b in buildings if b.get("demand") is not None}
    units |= {c.get("capacity_unit", "가구") for c in candidates if eligibility(c)["eligible"]}
    if len(units) > 1:
        raise ValueError("건물 수요와 후보 수용 기준의 단위를 하나로 맞춰 주세요.")
    ids = [c["candidate_id"] for c in candidates if eligibility(c)["eligible"]]
    # A는 첫 두 후보, B는 가용 후보 전체. 실제 분석에서는 settings로 후보 조합을 지정한다.
    a_ids = settings.get("plan_a_ids", ids[:2])
    b_ids = settings.get("plan_b_ids", ids)
    kwargs = {"max_distance_m": float(settings.get("max_distance_m", 600)),
              "balance_m": float(settings.get("balance_m", 120))}
    known_ids = {c["candidate_id"] for c in candidates}
    for chosen in (a_ids, b_ids):
        if not isinstance(chosen, list) or any(not isinstance(cid, str) for cid in chosen):
            raise ValueError("배치안 후보는 ID 목록으로 지정해 주세요.")
        if len(chosen) != len(set(chosen)) or set(chosen) - known_ids:
            raise ValueError("배치안의 중복 또는 미등록 후보 ID를 확인해 주세요.")
    if not all(math.isfinite(v) for v in kwargs.values()) or kwargs["max_distance_m"] <= 0 or kwargs["balance_m"] < 0:
        raise ValueError("거리 상한과 부하 가중치를 확인해 주세요.")
    a = make_plan("A", "A안 · 거점 수를 줄인 배치", buildings, candidates, a_ids, **kwargs)
    b = make_plan("B", "B안 · 여러 거점으로 분산", buildings, candidates, b_ids, **kwargs)
    def ranking(plan):
        m = plan["metrics"]
        return (m["unassigned_buildings"], m["max_distance_m"] if m["max_distance_m"] is not None else float("inf"), m["average_distance_m"] if m["average_distance_m"] is not None else float("inf"))
    ranked = sorted([a, b], key=ranking)
    return {"plans": [a, b], "suggested_plan": ranked[0]["plan_id"],
            "method": "안전 조건 제외 후 직선거리·수요·수용 기준으로 순차 배정",
            "limitations": "시연 수치와 단순 탐색 결과입니다. 실제 보행거리·차량 동선·배출량·안전 효과를 증명하지 않습니다.",
            "demand_unit": next(iter(units), "가구")}
