"""Relationship engine (prompt Section 10). Pure code, no AI.
Each edge is CLEAN, FLAGGED or NOT-TESTABLE. Thresholds are global constants, never per company.

Facts must use these canonical metric names (period like "Q1 FY27" or "FY26"):
  aum, gross_loans, stage3_amount, stage3_pct, stage2_amount, writeoffs, ppop, pbt,
  cost_of_funds, nim, crar, opex, net_total_income,
  segment_aum:<segment>, segment_stage3:<segment>
"""
import re
from collections import defaultdict

DIVERGE_PP = 10.0          # heuristic (i): growth gap of 10 percentage points or more
CONCENTRATION_X = 2.0      # R11: segment share of Stage 3 at least 2x its share of AUM
ADJ_GAP_WIDEN_PP = 0.25    # R3: write-off-adjusted minus reported GNPA widens by 0.25 pp or more


def period_key(p):
    """'Q1 FY27' -> (27, 1); 'FY26' -> (26, 4.5); unknown -> None."""
    s = (p or "").upper().replace(" ", "")
    m = re.match(r"Q([1-4])FY(\d{2,4})", s)
    if m:
        return (int(m.group(2)) % 100, int(m.group(1)))
    m = re.match(r"(?:H([12]))?FY(\d{2,4})", s)
    if m:
        return (int(m.group(2)) % 100, 4.5 if not m.group(1) else int(m.group(1)) * 2)
    m = re.search(r"(MAR|JUN|SEP|DEC)[A-Z]*[-]?(\d{4}|\d{2})$", s)     # '30 Jun 2026', '30-Jun-26', 'June 2026'
    if m:
        mon, yr = m.group(1), int(m.group(2)) % 100
        q = {"JUN": 1, "SEP": 2, "DEC": 3, "MAR": 4}[mon]
        return (yr + 1 if q in (1, 2, 3) else yr, q)                 # Indian FY: Jun 2026 = Q1 FY27
    return None


def to_label(p):
    """Normalise any period to 'Q1 FY27' / 'FY26' so quarters compare with quarters."""
    k = period_key(p)
    if not k:
        return p
    return f"FY{k[0]:02d}" if k[1] == 4.5 else f"Q{int(k[1])} FY{k[0]:02d}" if isinstance(k[1], int) else p


def _series(facts):
    """metric -> {period: value}, using one scope only (the most common one)."""
    scopes = defaultdict(int)
    for f in facts:
        scopes[f.get("scope", "")] += 1
    scope = max(scopes, key=scopes.get) if scopes else ""
    s = defaultdict(dict)
    for f in facts:
        if f.get("scope", "") == scope and period_key(f.get("period")):
            s[f["metric"].strip().lower()][to_label(f["period"])] = (float(f["value"]), f["id"])
    return s, scope


def _ends(series, metric, partner=None):
    """Earliest and latest comparable periods (same kind: quarters with quarters) shared with partner."""
    if metric not in series:
        return None
    ps = set(series[metric])
    if partner:
        if partner not in series:
            return None
        ps &= set(series[partner])
    for kind in ("Q", "FY"):
        same = sorted([p for p in ps if p.upper().startswith(kind)], key=period_key)
        if len(same) >= 2:
            return same[0], same[-1]
    return None


def _g(series, metric, a, b):
    va, vb = series[metric][a][0], series[metric][b][0]
    return (vb - va) / va * 100 if va else None


def _ids(series, metrics, periods):
    return sorted({series[m][p][1] for m in metrics for p in periods if p in series.get(m, {})})


def evaluate(facts):
    S, scope = _series(facts)
    out = []

    def add(rid, name, status, detail="", ids=()):
        out.append({"id": rid, "relationship": name, "status": status, "detail": detail, "fact_ids": list(ids)})

    # R1 loan growth vs Stage 3 rupees vs ratio
    base = "aum" if _ends(S, "aum", "stage3_amount") else "gross_loans"
    e = _ends(S, base, "stage3_amount")
    if e:
        ga, gs = _g(S, base, *e), _g(S, "stage3_amount", *e)
        flag = gs - ga >= DIVERGE_PP
        ratio_down = "stage3_pct" in S and all(p in S["stage3_pct"] for p in e) and \
            S["stage3_pct"][e[1]][0] < S["stage3_pct"][e[0]][0] and gs > 0
        st = "FLAGGED" if flag or ratio_down else "CLEAN"
        add("R1", "Loan growth vs Stage 3 rupees vs GNPA %", st,
            f"{e[0]}->{e[1]}: {base} growth {ga:.1f}%, Stage 3 rupee growth {gs:.1f}%"
            + ("; ratio fell while rupees rose" if ratio_down else ""),
            _ids(S, [base, "stage3_amount", "stage3_pct"], e))
    else:
        add("R1", "Loan growth vs Stage 3 rupees vs GNPA %", "NOT-TESTABLE", "needs aum/gross_loans and stage3_amount for 2 periods")

    # R2 Stage 2 vs Stage 3 (migration)
    e = _ends(S, "stage2_amount", "stage3_amount")
    if e:
        d2 = S["stage2_amount"][e[1]][0] - S["stage2_amount"][e[0]][0]
        d3 = S["stage3_amount"][e[1]][0] - S["stage3_amount"][e[0]][0]
        opposite = d2 * d3 < 0 and min(abs(d2), abs(d3)) >= 0.5 * max(abs(d2), abs(d3))
        add("R2", "Stage 2 rupees vs Stage 3 rupees", "FLAGGED" if opposite else "CLEAN",
            f"{e[0]}->{e[1]}: Stage 2 change {d2:,.0f}, Stage 3 change {d3:,.0f}",
            _ids(S, ["stage2_amount", "stage3_amount"], e))
    else:
        add("R2", "Stage 2 rupees vs Stage 3 rupees", "NOT-TESTABLE", "needs stage2_amount and stage3_amount for 2 periods")

    # R3 reported vs write-off-adjusted GNPA
    e = _ends(S, "writeoffs", "stage3_amount")
    if e and all(p in S.get("gross_loans", {}) for p in e):
        gaps = []
        for p in e:
            st3, wo, gl = S["stage3_amount"][p][0], S["writeoffs"][p][0], S["gross_loans"][p][0]
            gaps.append((st3 + wo) / (gl + wo) * 100 - st3 / gl * 100)
        add("R3", "Reported GNPA vs write-off-adjusted GNPA", "FLAGGED" if gaps[1] - gaps[0] >= ADJ_GAP_WIDEN_PP else "CLEAN",
            f"adjusted-minus-reported gap {gaps[0]:.2f}pp ({e[0]}) -> {gaps[1]:.2f}pp ({e[1]})",
            _ids(S, ["writeoffs", "stage3_amount", "gross_loans"], e))
    else:
        add("R3", "Reported GNPA vs write-off-adjusted GNPA", "NOT-TESTABLE", "needs writeoffs, stage3_amount, gross_loans for 2 periods")

    add("R4", "Coverage vs stage mix vs secured share", "NOT-TESTABLE", "not collected in this run")

    # R5 PBT growth vs PPOP growth
    e = _ends(S, "ppop", "pbt")
    if e:
        gp, gb = _g(S, "ppop", *e), _g(S, "pbt", *e)
        add("R5", "PPOP growth vs PBT growth (provisions)", "FLAGGED" if gb - gp >= DIVERGE_PP else "CLEAN",
            f"{e[0]}->{e[1]}: PPOP growth {gp:.1f}%, PBT growth {gb:.1f}%", _ids(S, ["ppop", "pbt"], e))
    else:
        add("R5", "PPOP growth vs PBT growth (provisions)", "NOT-TESTABLE", "needs ppop and pbt for 2 periods")

    # R6 cost of funds vs NIM
    e = _ends(S, "cost_of_funds", "nim")
    if e:
        dc = S["cost_of_funds"][e[1]][0] - S["cost_of_funds"][e[0]][0]
        dn = S["nim"][e[1]][0] - S["nim"][e[0]][0]
        add("R6", "Cost of funds vs NIM", "FLAGGED" if dc < 0 and dn <= 0 else "CLEAN",
            f"{e[0]}->{e[1]}: cost of funds {dc:+.2f}pp, NIM {dn:+.2f}pp", _ids(S, ["cost_of_funds", "nim"], e))
    else:
        add("R6", "Cost of funds vs NIM", "NOT-TESTABLE", "needs cost_of_funds and nim for 2 periods")

    for rid, nm in [("R7", "Short-term funding vs ALM vs LCR"), ("R8", "Lender concentration vs off-book"),
                    ("R9", "Contingent liabilities vs net worth")]:
        add(rid, nm, "NOT-TESTABLE", "not collected in this run")

    # R10 CRAR trend
    crar = sorted(S.get("crar", {}).items(), key=lambda kv: period_key(kv[0]))
    if len(crar) >= 3:
        falling = all(crar[i + 1][1][0] < crar[i][1][0] for i in range(len(crar) - 1))
        add("R10", "Capital (CRAR) vs growth", "FLAGGED" if falling else "CLEAN",
            " -> ".join(f"{p}: {v[0]}" for p, v in crar), [v[1] for _, v in crar])
    else:
        add("R10", "Capital (CRAR) vs growth", "NOT-TESTABLE", "needs crar for 3 periods")

    # R11 segment concentration
    segs = {m.split(":", 1)[1] for m in S if m.startswith("segment_aum:")}
    flagged, notes, ids = False, [], []
    for sg in segs:
        a, s3 = S.get(f"segment_aum:{sg}", {}), S.get(f"segment_stage3:{sg}", {})
        common = [p for p in a if p in s3 and p in S.get("aum", {}) and p in S.get("stage3_amount", {})]
        if common:
            p = max(common, key=period_key)
            sa = a[p][0] / S["aum"][p][0]; ss = s3[p][0] / S["stage3_amount"][p][0]
            notes.append(f"{sg} ({p}): {sa:.1%} of AUM, {ss:.1%} of Stage 3")
            ids += [a[p][1], s3[p][1], S["aum"][p][1], S["stage3_amount"][p][1]]
            flagged |= sa > 0 and ss / sa >= CONCENTRATION_X
    add("R11", "Segment share of Stage 3 vs share of AUM",
        ("FLAGGED" if flagged else "CLEAN") if notes else "NOT-TESTABLE",
        "; ".join(notes) or "needs segment_aum:<x> and segment_stage3:<x>", ids)

    for rid, nm in [("R12", "Management claims vs later numbers"), ("R13", "Governance events vs accounting changes"),
                    ("R14", "Company vs peer medians"), ("R15", "Rating actions vs company disclosures")]:
        add(rid, nm, "NOT-TESTABLE", "judged or peer data not collected by code in this run")

    e = _ends(S, "opex", "net_total_income")
    if e:
        c0 = S["opex"][e[0]][0] / S["net_total_income"][e[0]][0] * 100
        c1 = S["opex"][e[1]][0] / S["net_total_income"][e[1]][0] * 100
        add("R16", "Cost-to-income vs growth", "FLAGGED" if c1 - c0 >= 2 else "CLEAN",
            f"cost-to-income {c0:.1f}% ({e[0]}) -> {c1:.1f}% ({e[1]})", _ids(S, ["opex", "net_total_income"], e))
    else:
        add("R16", "Cost-to-income vs growth", "NOT-TESTABLE", "needs opex and net_total_income for 2 periods")
    add("R17", "Customer/product mix vs segment delinquency", "NOT-TESTABLE", "not collected in this run")

    counts = defaultdict(int)
    for r in out:
        counts[r["status"]] += 1
    return {"scope_used": scope, "summary": dict(counts), "edges": out}
