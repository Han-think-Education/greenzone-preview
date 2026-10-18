"""기존 SQLite에 후보·근거·규칙 자료를 추가하는 작은 데이터 계층."""
from datetime import datetime, timezone
import json
from pathlib import Path
from backend.analysis import compare_plans, eligibility


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def add_tables(db, catalog_path: Path):
    columns = {r[1] for r in db.execute("PRAGMA table_info(buildings)")}
    extra = {"lat": "REAL", "lon": "REAL", "demand": "REAL", "demand_unit": "TEXT", "source_id": "TEXT", "checked_at": "TEXT", "is_demo": "INTEGER NOT NULL DEFAULT 1"}
    for name, kind in extra.items():
        if name not in columns:
            db.execute(f"ALTER TABLE buildings ADD COLUMN {name} {kind}")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS candidates (
        candidate_id TEXT PRIMARY KEY, name TEXT NOT NULL,
        lat REAL, lon REAL, capacity REAL, capacity_unit TEXT,
        truck_access TEXT NOT NULL DEFAULT 'unknown', stopping_space TEXT NOT NULL DEFAULT 'unknown',
        work_space TEXT NOT NULL DEFAULT 'unknown', pedestrian_clear TEXT NOT NULL DEFAULT 'unknown',
        review_status TEXT NOT NULL DEFAULT 'review', rationale TEXT NOT NULL DEFAULT '',
        safety_note TEXT NOT NULL DEFAULT '', source_id TEXT, checked_at TEXT,
        is_demo INTEGER NOT NULL DEFAULT 1, revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS sources (
        source_id TEXT PRIMARY KEY, title TEXT NOT NULL, url TEXT, reference_date TEXT, note TEXT
    );
    CREATE TABLE IF NOT EXISTS rules (
        rule_id TEXT PRIMARY KEY, category TEXT UNIQUE NOT NULL, days TEXT, time_text TEXT,
        guidance TEXT NOT NULL, source_id TEXT, source_url TEXT, reference_date TEXT,
        verification_status TEXT NOT NULL DEFAULT 'unverified', is_demo INTEGER NOT NULL DEFAULT 1,
        revision INTEGER NOT NULL DEFAULT 1, updated_at TEXT
    );
    CREATE TABLE IF NOT EXISTS catalog_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS change_history (
        change_id INTEGER PRIMARY KEY AUTOINCREMENT, entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL, changed_at TEXT NOT NULL, changes TEXT NOT NULL
    );
    """)
    candidate_columns = {r[1] for r in db.execute('PRAGMA table_info(candidates)')}
    if 'analysis_active' not in candidate_columns:
        db.execute('ALTER TABLE candidates ADD COLUMN analysis_active INTEGER NOT NULL DEFAULT 1')
    if not catalog_path.exists():
        return
    seed = json.loads(catalog_path.read_text(encoding="utf-8"))
    if seed.get('study_area', {}).get('is_demo') is False:
        current_candidates = {r['candidate_id'] for r in seed.get('candidates', [])}
        for old in db.execute("SELECT candidate_id FROM candidates WHERE source_id='VWORLD_ROADS' AND is_demo=0").fetchall():
            db.execute('UPDATE candidates SET analysis_active=? WHERE candidate_id=?', (int(old[0] in current_candidates),old[0]))
    # 사용자 요청: 기존 가상 위치와 그 위치에 대한 시연 요청만 제거. 공식·수동 자료는 보존.
    if seed.get('study_area', {}).get('is_demo') is False:
        old_buildings = [r[0] for r in db.execute("SELECT building_id FROM buildings WHERE is_demo=1 AND source_id='DEMO'")]
        for bid in old_buildings:
            db.execute("DELETE FROM disposal_requests WHERE building_id=?", (bid,))
            db.execute("DELETE FROM buildings WHERE building_id=? AND is_demo=1 AND source_id='DEMO'", (bid,))
        db.execute("DELETE FROM candidates WHERE is_demo=1 AND source_id='DEMO'")
        db.execute("DELETE FROM zones WHERE zone_id IN ('A','B','C') AND NOT EXISTS (SELECT 1 FROM buildings WHERE buildings.zone_id=zones.zone_id)")
        db.execute("DELETE FROM sources WHERE source_id='DEMO' AND NOT EXISTS (SELECT 1 FROM candidates WHERE source_id='DEMO') AND NOT EXISTS (SELECT 1 FROM buildings WHERE source_id='DEMO')")
        for key in ('study_area','analysis_settings'):
            db.execute("INSERT INTO catalog_meta VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value", (key,json.dumps(seed.get(key,{}),ensure_ascii=False)))
    for key in ("study_area", "analysis_settings"):
        db.execute("INSERT OR IGNORE INTO catalog_meta VALUES (?,?)", (key, json.dumps(seed.get(key, {}), ensure_ascii=False)))
    specs = {
        "sources": ("source_id", "title", "url", "reference_date", "note"),
        "candidates": ("candidate_id", "name", "lat", "lon", "capacity", "capacity_unit", "truck_access", "stopping_space", "work_space", "pedestrian_clear", "review_status", "rationale", "safety_note", "source_id", "checked_at", "is_demo"),
        "rules": ("rule_id", "category", "days", "time_text", "guidance", "source_id", "source_url", "reference_date", "verification_status", "is_demo"),
    }
    for table, fields in specs.items():
        for row in seed.get(table, []):
            record = {f: row.get(f) for f in fields}
            if table != "sources":
                record["updated_at"] = now_iso()
            primary_key = {"sources": "source_id", "candidates": "candidate_id", "rules": "rule_id"}[table]
            db.execute(f"INSERT INTO {table} ({','.join(record)}) VALUES ({','.join('?' for _ in record)}) ON CONFLICT({primary_key}) DO NOTHING", tuple(record.values()))
            if table == 'candidates' and row.get('source_id') == 'VWORLD_ROADS' and row.get('is_demo') == 0:
                db.execute('UPDATE candidates SET analysis_active=1 WHERE candidate_id=?', (row['candidate_id'],))
                # 새 분석 좌표는 미수정 조사 기준점에만 반영. 담당자 수정(revision>1)은 보존.
                names = ('name','lat','lon','rationale','safety_note','checked_at')
                db.execute('UPDATE candidates SET '+','.join(n+'=?' for n in names)+" WHERE candidate_id=? AND source_id='VWORLD_ROADS' AND revision=1 AND truck_access='unknown' AND stopping_space='unknown' AND work_space='unknown' AND pedestrian_clear='unknown'",
                           tuple(row.get(n) for n in names)+(row['candidate_id'],))
    fields = ("building_id", "zone_id", "building_name", "road_address", "verification_status", "lat", "lon", "demand", "demand_unit", "source_id", "checked_at", "is_demo")
    current_ids = {r['building_id'] for r in seed.get('buildings', []) if r.get('source_id') == 'PILOT_OFFICIAL_BUILDINGS'}
    if current_ids:
        for old in db.execute("SELECT building_id FROM buildings WHERE source_id='PILOT_OFFICIAL_BUILDINGS'").fetchall():
            if old[0] not in current_ids:
                # 용도 재분류로 대상에서 빠진 실제 기록은 삭제하지 않고 배정 수요만 해제한다.
                db.execute("UPDATE buildings SET demand=NULL,verification_status='source_checked_context_only_not_disposal_approved' WHERE building_id=? AND source_id='PILOT_OFFICIAL_BUILDINGS'", (old[0],))
    for row in seed.get("buildings", []):
        bid, zid = row["building_id"], row.get("zone_id", "A")
        db.execute("INSERT OR IGNORE INTO zones VALUES (?,?,0)", (zid, f"권역 {zid}"))
        db.execute(f"INSERT INTO buildings ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)}) ON CONFLICT(building_id) DO NOTHING", tuple(row.get(f) for f in fields))
        if row.get('source_id') == 'PILOT_OFFICIAL_BUILDINGS':
            db.execute("UPDATE buildings SET demand=?,verification_status=? WHERE building_id=? AND source_id='PILOT_OFFICIAL_BUILDINGS' AND verification_status='source_checked_context_only_not_disposal_approved'", (row.get('demand'),row.get('verification_status'),bid))
        # 이전 가상 샘플의 빈 좌표만 채운다. 기존 실제 자료·담당자 수정은 보존한다.
        db.execute("UPDATE buildings SET lat=?,lon=?,demand=?,demand_unit=?,source_id=?,checked_at=?,is_demo=? WHERE building_id=? AND lat IS NULL AND road_address LIKE 'ZONE-% 시연용 가상 주소'", (row.get("lat"), row.get("lon"), row.get("demand"), row.get("demand_unit"), row.get("source_id"), row.get("checked_at"), row.get("is_demo", 1), bid))


def read_catalog(connection) -> dict:
    with connection() as db:
        data = {name: [dict(r) for r in db.execute(f"SELECT * FROM {name}")] for name in ("candidates", "buildings", "sources", "rules", "zones")}
        meta = {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM catalog_meta")}
    data.update(meta)
    data['archived_candidate_count'] = sum(not c.get('analysis_active', 1) for c in data['candidates'])
    data['candidates'] = [c for c in data['candidates'] if c.get('analysis_active', 1)]
    data["candidates"].sort(key=lambda c: c["candidate_id"])
    data["buildings"].sort(key=lambda b: b["building_id"])
    for c in data["candidates"]:
        c["eligibility"] = eligibility(c)
    if not any(c['eligibility']['eligible'] for c in data['candidates']):
        data['analysis'] = {'plans':[], 'suggested_plan':None, 'method':'공식 자료 사전 분석. 도로 기반 조사 기준점의 안전·수용 조건 미확인으로 운영 배정은 하지 않음.'}
        return data
    try:
        active_buildings = [b for b in data['buildings'] if b.get('verification_status') != 'source_checked_context_only_not_disposal_approved']
        data["analysis"] = compare_plans(active_buildings, data["candidates"], data.get("analysis_settings"))
    except ValueError as error:
        data["analysis"] = {"plans": [], "suggested_plan": None, "error": str(error)}
    return data
