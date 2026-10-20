"""Provenance store, code-level fact verification, lead register and scoring.
Machine-checked inputs (families, tiers, document count, verification, code-reproduced numbers)
are computed HERE from the logs. The model only supplies the judged yes/no answers."""
import json, re

import scoring
from agent import DATA, relationships

FACTS = DATA / "facts_company.json"
LEADS = DATA / "leads.json"
CALC_LOG = DATA / "calc_log.json"


def _load(p):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else []


def _dump(p, obj):
    p.write_text(json.dumps(obj, indent=2, ensure_ascii=False), encoding="utf-8")


def reset():
    DATA.mkdir(parents=True, exist_ok=True)
    for p in (FACTS, LEADS, CALC_LOG, DATA / "documents.json"):
        _dump(p, [])


# ----------------------------------------------------------------------------- verification
def _num_forms(v):
    v = float(v)
    forms = {f"{v:.2f}", f"{v:.1f}"}
    if abs(v - round(v)) < 1e-9:
        forms.add(str(int(round(v))))
    return {f.rstrip("0").rstrip(".") if "." in f else f for f in forms} | forms


def verify_fact(f):
    """Re-open the saved page and check (1) the excerpt words and (2) the number really appear there."""
    from agent.tools_parse import page_text
    try:
        page = int(str(f.get("page", "")).split("-")[0])
        text = page_text(f["doc"], page)
    except Exception as e:
        return False, f"could not re-open page ({type(e).__name__})"
    if not text.strip():
        return False, "page has no extractable text"
    flat = re.sub(r"\s+", " ", text.lower())
    nocomma = flat.replace(",", "")
    words = [w for w in re.findall(r"[a-z0-9.]+", f.get("excerpt", "").lower()) if len(w) >= 3]
    overlap = sum(w.replace(",", "") in nocomma for w in words) / max(1, len(words))
    value_ok = any(re.search(r"(?<![0-9.])" + re.escape(s) + r"(?![0-9])", nocomma)
                   for s in _num_forms(f["value"]))
    if overlap < 0.6:
        return False, f"excerpt not found on page {page} (word overlap {overlap:.0%})"
    if not value_ok:
        return False, f"value {f['value']} not found on page {page}"
    return True, f"excerpt and value found on page {page}"


def save_facts(facts):
    from agent.tools_web import DOCS
    store = _load(FACTS)
    out = []
    for a in facts:
        a = dict(a)
        doc = next((d for d in DOCS if a.get("doc") in (d["id"], d.get("file"))), None)
        if doc:
            a.setdefault("source_url", doc["url"])
            a["tier"], a["family"] = doc["tier"], doc["family"]
        a["id"] = f"F{len(store) + 1:03d}"
        ok, why = verify_fact(a) if doc else (False, "unknown document id")
        a["verified"], a["verify_note"] = ok, why
        store.append(a)
        out.append({"id": a["id"], "metric": a.get("metric"), "period": a.get("period"),
                    "verified": ok, "note": why})
    _dump(FACTS, store)
    return out


# ----------------------------------------------------------------------------- relationships
def get_relationships():
    facts = [f for f in _load(FACTS) if f.get("verified")]
    if not facts:
        return {"error": "no verified facts saved yet"}
    res = relationships.evaluate(facts)
    _dump(DATA / "relationships.json", res)
    return res


# ----------------------------------------------------------------------------- leads + scoring
DIMS = list(scoring.DIMS_V4)


def save_lead(lead):
    leads = [l for l in _load(LEADS) if l.get("id") != lead.get("id")]
    tests = lead.get("tests", {})
    for d in DIMS:
        vals = tests.get(d)
        if not isinstance(vals, list) or len(vals) != 5:
            return {"error": f"tests.{d} must be a list of 5 true/false values"}
    leads.append(lead)
    _dump(LEADS, leads)
    return {"saved": lead["id"], "leads_in_register": len(leads)}


def _machine_inputs(lead, facts, calcs):
    fs = [facts[i] for i in lead.get("fact_ids", []) if i in facts]
    fams = {f.get("family") for f in fs if f.get("family") and f.get("family") not in ("X", "A?")}
    cs = [calcs[i] for i in lead.get("calc_ids", []) if i in calcs]
    return dict(
        independent_families=len(fams),
        has_tier1_or_2=any((f.get("tier") or 9) <= 2 for f in fs),
        source_documents=len({f.get("doc") for f in fs}),
        claims_verified=bool(fs) and all(f.get("verified") for f in fs),
        reproduced=bool(cs),
        families=sorted(fams))


def score_leads():
    raw = _load(LEADS)
    if not raw:
        return {"error": "no leads saved yet"}
    facts = {f["id"]: f for f in _load(FACTS)}
    calcs = {c["id"]: c for c in _load(CALC_LOG)}
    leads, machine = [], {}
    for r in raw:
        mi = _machine_inputs(r, facts, calcs)
        machine[r["id"]] = mi
        tests = {d: [bool(x) for x in r["tests"][d]] for d in DIMS}
        if not r.get("fact_ids"):                         # a pass without evidence counts as a fail
            tests = {d: [False] * 5 for d in DIMS}
        # machine-checked tests are overwritten from the logs (the model cannot award them)
        tests["evidence"][1] = mi["reproduced"]
        tests["evidence"][2] = mi["claims_verified"]
        tests["cross_source"][0] = mi["independent_families"] >= 2
        tests["cross_source"][1] = mi["independent_families"] >= 3
        tests["discovery"][2] = mi["source_documents"] >= 2
        tests["discovery"][3] = mi["reproduced"]
        tests["robustness"][0] = int(r.get("counter_categories_searched", 0)) >= 4
        leads.append(scoring.Lead(
            id=r["id"], name=r.get("name", ""), tests=tests,
            independent_families=mi["independent_families"], has_tier1_or_2=mi["has_tier1_or_2"],
            counter_categories_searched=int(r.get("counter_categories_searched", 0)),
            falsification_criteria_met=int(r.get("falsification_criteria_met", 0)),
            confounders_checked=bool(r.get("confounders_checked", False)),
            claims_verified=mi["claims_verified"], source_documents=mi["source_documents"],
            unresolved_strong_counter=bool(r.get("unresolved_strong_counter", False)),
            unresolved_conflict=bool(r.get("unresolved_conflict", False)),
            counter_strength=r.get("counter_strength", "Weak"),
            counter_resolved=bool(r.get("counter_resolved", False)),
            is_company_headline=bool(r.get("is_company_headline", False))))
    rows, verdict = scoring.score_all(leads)
    for row in rows:
        row["machine_inputs"] = machine[row["id"]]
    top = next((r for r in rows if r["gates_passed"]), None)
    if top is None or top["final"] < 50:
        verdict = "No Strong Finding (no lead passed all gates with a score of 50 or more)"
    res = {"verdict": verdict, "rows": rows}
    _dump(DATA / "scores.json", res)
    return res
