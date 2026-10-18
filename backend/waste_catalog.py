"""공식 품목표의 정확 검색. 금액·규격을 LLM으로 생성하거나 추정하지 않는다."""
from datetime import date
import json
from pathlib import Path
import re
import unicodedata

ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data/waste_catalog.json"


def normalize(text):
    return re.sub(r"[^가-힣a-z0-9]", "", unicodedata.normalize("NFKC", text).lower())


def create_tables(db):
    db.executescript((ROOT / "data/waste_schema.sql").read_text(encoding="utf-8"))
    columns = {r[1] for r in db.execute("PRAGMA table_info(sources)")}
    for name in ("checked_at", "content_hash"):
        if name not in columns:
            db.execute(f"ALTER TABLE sources ADD COLUMN {name} TEXT")


def sync_catalog(db, path=DATA_PATH):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data["schema_version"] != 1 or not data["items"] or not data["rules"]:
        raise ValueError("품목 자료의 형식·내용을 확인하세요")
    ids = {}
    for key, field in (("sources", "source_id"), ("items", "item_id"), ("aliases", "alias_id"), ("rules", "rule_id")):
        ids[key] = {row[field] for row in data[key]}
        if len(ids[key]) != len(data[key]):
            raise ValueError("품목 자료 ID가 중복됩니다")
    for item in data["items"]:
        if item["source_id"] not in ids["sources"] or not item["official_name"].strip():
            raise ValueError("품목 출처·명칭을 확인하세요")
    for row in data["aliases"]:
        if row["item_id"] not in ids["items"] or len(normalize(row["alias"])) < 2:
            raise ValueError("검색어 연결을 확인하세요")
    for row in data["rules"]:
        if (row["item_id"] not in ids["items"] or row["source_id"] not in ids["sources"]
                or row["guide_source_id"] not in ids["sources"] or not re.fullmatch(r"\d{5}", row["district_code"])
                or row["snapshot_id"] != data["snapshot_id"] or not row["specification"].strip()):
            raise ValueError("품목별 규칙 연결을 확인하세요")
        fee = row["fee_krw"]
        if fee is not None and (type(fee) is not int or fee < 0):
            raise ValueError("금액은 0 이상의 정수 또는 미확인(null)이어야 합니다")
        for name in ("checked_at", "reference_date", "effective_from", "effective_until"):
            if row[name]:
                date.fromisoformat(row[name])
        if row["effective_from"] and row["effective_until"] and row["effective_from"] > row["effective_until"]:
            raise ValueError("시행기간을 확인하세요")
    # 파일 전체 연결을 확인한 후 한 트랜잭션에서 가져온다. 다른 거점·규칙·관리자 자료는 수정하지 않는다.
    for row in data["sources"]:
        fields = tuple(row)
        updates = ",".join(f"{key}=excluded.{key}" for key in fields if key != "source_id")
        db.execute(f"INSERT INTO sources ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)}) ON CONFLICT(source_id) DO UPDATE SET {updates}", tuple(row.values()))
    for key, table, primary in (("items", "waste_items", "item_id"), ("aliases", "item_aliases", "alias_id"), ("rules", "item_rules", "rule_id")):
        for original in data[key]:
            row = dict(original)
            if key == "aliases":
                row.update(normalized_alias=normalize(row["alias"]), active=1)
            row["managed_by"] = "official_seed"
            fields = tuple(row)
            updates = ",".join(f"{field}=excluded.{field}" for field in fields if field != primary)
            db.execute(f"INSERT INTO {table} ({','.join(fields)}) VALUES ({','.join('?' for _ in fields)}) ON CONFLICT({primary}) DO UPDATE SET {updates} WHERE {table}.managed_by='official_seed'", tuple(row.values()))
        # 이번 파일에 없는 옛 자동등록 항목은 삭제 대신 비활성화한다. 수동 등록 자료는 보존한다.
        source_ids = tuple(ids["sources"])
        placeholders = ','.join('?' for _ in source_ids)
        if key == 'aliases':
            scope = f"item_id IN (SELECT item_id FROM waste_items WHERE source_id IN ({placeholders}))"
        else:
            scope = f"source_id IN ({placeholders})"
        for old in db.execute(f"SELECT {primary} FROM {table} WHERE managed_by='official_seed' AND {scope}", source_ids).fetchall():
            if old[0] not in ids[key]:
                db.execute(f"UPDATE {table} SET active=0 WHERE {primary}=? AND managed_by='official_seed'", (old[0],))
    return {"item_count": len(data["items"]), "rule_count": len(data["rules"]), "alias_count": len(data["aliases"])}


def match_items(db, query):
    text = normalize(query)
    hits = []
    rows = db.execute("""SELECT a.item_id,a.normalized_alias,i.official_name,i.official_category
        FROM item_aliases a JOIN waste_items i ON a.item_id=i.item_id
        WHERE a.active=1 AND i.active=1""").fetchall()
    for row in rows:
        alias = row["normalized_alias"]
        start = text.find(alias)
        while start >= 0:
            hits.append((start, start + len(alias), row))
            start = text.find(alias, start + 1)
    result = {}
    for start, end, row in hits:
        # 「안마의자」 안의 「의자」, 「김치냉장고」 안의 「냉장고」를 별도 품목으로 오인하지 않는다.
        if any(s <= start and end <= e and e - s > end - start for s, e, _ in hits):
            continue
        result[row["item_id"]] = {"item_id": row["item_id"], "official_name": row["official_name"], "official_category": row["official_category"]}
    return sorted(result.values(), key=lambda item: item["official_name"])


def search(connection, query, district_code="11470", context_item_id=None):
    from backend.knowledge import requested_other_area, today_kst
    if requested_other_area(query, district_code):
        return {"mode": "out_of_scope", "items": [], "message": "현재 품목 DB는 양천구 자료입니다. 다른 지역의 수수료로 적용할 수 없습니다."}
    today = today_kst().isoformat()
    with connection() as db:
        items = match_items(db, query)
        if not items and context_item_id:
            row = db.execute("SELECT item_id,official_name,official_category FROM waste_items WHERE item_id=? AND active=1", (context_item_id,)).fetchone()
            if row:
                items = [dict(row)]
        found = []
        for item in items:
            rules = [dict(r) for r in db.execute("""SELECT r.*,s.title AS source_title,s.url AS source_url,
                g.url AS guide_url,g.title AS guide_title FROM item_rules r
                JOIN sources s ON r.source_id=s.source_id JOIN sources g ON r.guide_source_id=g.source_id
                WHERE r.item_id=? AND r.district_code=? AND r.active=1 AND r.verification_status='source_checked'
                AND (r.effective_from IS NULL OR r.effective_from<=?)
                AND (r.effective_until IS NULL OR r.effective_until>=?)
                ORDER BY r.fee_krw,r.source_item_code""", (item["item_id"], district_code, today, today))]
            if rules:
                found.append({**item, "rules": rules})
    return {"mode": "item_database" if found else "no_match", "items": found,
            "message": "공식 품목명·프로젝트 검색어로 조회. 규격은 원문 그대로 표시하며 자동 선택하지 않습니다."}


def specification_matches(query, item, rules):
    text = normalize(query)
    name = normalize(item['official_name'])
    if text.startswith(name):
        text = text[len(name):]
    # 수치 추정·부분문자열 비교 대신 공식 규격 전체와 단순 응답 어미만 허용한다.
    endings = ('', '이에요', '예요', '입니다', '이요', '요', '짜리', '비용', '얼마인가요')
    return [r for r in rules if any(text == normalize(r['specification']) + ending for ending in endings)]


def answer(connection, query, district_code="11470", context=None):
    found = search(connection, query, district_code)
    if not found['items'] and found['mode'] != 'out_of_scope' and context and context.get('district_code') == district_code and context.get('pending') == 'specification':
        previous = search(connection, query, district_code, context.get('item_id'))
        if len(previous['items']) == 1 and specification_matches(query, previous['items'][0], previous['items'][0]['rules']):
            found = previous
    if not found["items"]:
        if found['mode'] != 'out_of_scope' and re.search(r'가구|작은\s*물건|소형\s*물건', query):
            return {"category": "bulky", "mode": "item_clarification", "ai_used": False,
                    "response": "‘작은 가구’만으로는 수수료를 정하기 어려워요. 어떤 물건인가요? 의자·책상·서랍장처럼 품목명을 알려주세요. 그다음 공식 표의 크기·형태별 규격을 함께 확인할게요. 작다고 모두 같은 요금이거나 무료인 것은 아니에요.",
                    "suggestions": [{"label": n, "message": n+' 배출 비용'} for n in ['의자','책상','서랍장']],
                    "context": {"district_code": district_code, "pending": "item", "item_id": None},
                    "verification_status": "needs_item_details", "is_demo": True, "citations": [],
                    "retrieval": {"mode": "clarification", "embedding_used": False, "answer_generated": False,
                                  "message": "금액을 추정하지 않고 품목을 먼저 확인합니다."}}
        return None
    if len(found["items"]) > 1:
        names = [row["official_name"] for row in found["items"]]
        return {"category": "bulky", "mode": "item_clarification", "ai_used": False,
                "response": "여러 품목이 검색됐어요: " + ", ".join(names) + ".\n품목 하나와 규격을 알려주세요. 각 품목의 수수료가 달라 임의로 선택하지 않을게요.",
                "verification_status": "source_checked", "is_demo": True, "citations": [],
                "context": None, "suggestions": [{"label": n, "message": n+' 배출 비용'} for n in names[:8]],
                "retrieval": {"mode": "item_database", "embedding_used": False, "answer_generated": False,
                              "message": "품목 DB 조회 · 추가 품목 확인 필요"}}
    item = found["items"][0]
    rules = item["rules"]
    selected = specification_matches(query, item, rules)
    all_rules = rules
    if len(selected) == 1:
        rules = selected
    first = rules[0]
    lines = [f"양천구 공식 품목표에서 ‘{item['official_name']}’를 찾았어요."]
    fee_lines = []
    for row in rules:
        price = f"{row['fee_krw']:,}원" if row["fee_krw"] is not None else "수수료 미확인"
        fee_lines.append(f"• {row['specification']} — {price}")
    lines.extend(fee_lines)
    if len(rules) > 1:
        lines.append("어떤 규격인가요? 아래에서 고르거나 공식 규격명을 입력해 주세요. ‘작다’는 표현만으로 크기·금액을 선택하지 않을게요.")
    elif selected:
        lines.append("말씀하신 규격과 공식 표의 명칭을 맞춰 조회한 금액이에요. 실제 물건이 이 규격에 해당하는지는 신청 시 확인해 주세요.")
    conditions = sorted({r["conditions"] for r in rules if r["conditions"]})
    lines.extend(conditions)
    if item["official_category"] == '가전제품류' and not conditions:
        lines.append("일부 가전제품은 무상수거 대상일 수 있어요. 이 제품의 대상 여부는 공식 폐가전 안내에서 별도로 확인해야 해요.")
    procedure = "신고자 정보·휴대폰 인증 → 배출 장소·일시와 품목 입력 → 수수료 결제 → 배출증 부착 후 신고한 장소에 배출하는 절차예요."
    lines.extend([procedure, "배출일 전날까지 신고하고 수거는 배출일 다음날부터 순차 진행하며, 주말·공휴일은 제외돼요. 지연될 수 있어요.",
                  "일반적인 제품보다 크기·무게가 2배 이상 차이 나면 가격이 달라질 수 있어요. 목록에 있다는 것이 개별 수거 승인을 뜻하지는 않아요.",
                  f"자료 확인일: {first['checked_at']} · 시행기간은 원문에 명시되지 않았어요. 결제 전 최신 원문을 확인해 주세요.",
                  "이 서비스는 신고·결제를 대신하지 않으며 지도 후보를 실제 배출 장소로 안내하지 않아요."])
    citation = {"document_id": "ITEM-" + item["item_id"], "title": item["official_name"] + " 규격별 수수료",
                "text": "\n".join(fee_lines + conditions), "source_url": first["source_url"],
                "district_name": first["district_name"], "checked_at": first["checked_at"],
                "reference_date": first["reference_date"], "effective_from": first["effective_from"],
                "effective_until": first["effective_until"], "search_method": "item_database"}
    guide = {**citation, "document_id": "YC_BULKY_GUIDE", "title": first["guide_title"],
             "text": procedure, "source_url": first["guide_url"]}
    return {"category": "bulky", "mode": "item_database", "ai_used": False,
            "context": {"district_code": district_code, "pending": "specification", "item_id": item['item_id']},
            "suggestions": [{"label": r['specification'].strip(), "message": item['official_name']+' · '+r['specification'].strip()} for r in all_rules[:20]] if len(rules)>1 else [],
            "response": "\n".join(lines), "verification_status": "source_checked", "is_demo": True,
            "citations": [citation, guide],
            "retrieval": {"mode": "item_database", "embedding_used": False, "answer_generated": False,
                          "message": "공식 품목 DB 직접 조회 · 비용/규격 자동 추정 없음"}}


def status(connection):
    with connection() as db:
        return {"item_count": db.execute("SELECT COUNT(*) FROM waste_items WHERE active=1").fetchone()[0],
                "rule_count": db.execute("SELECT COUNT(*) FROM item_rules WHERE active=1").fetchone()[0],
                "alias_count": db.execute("SELECT COUNT(*) FROM item_aliases WHERE active=1").fetchone()[0],
                "checked_at": db.execute("SELECT MAX(checked_at) FROM item_rules WHERE active=1").fetchone()[0],
                "scope": "양천구 대형생활폐기물 공식 수수료표", "model_called": False}
