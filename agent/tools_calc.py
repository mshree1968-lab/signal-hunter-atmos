"""calculate(): every number the report uses is computed here, never by the model.
Inputs may be numbers or fact ids (e.g. "F003"); fact ids are looked up in the provenance store."""
import json

import archetypes as arch
import metrics as m
from agent import DATA

CALC_LOG = DATA / "calc_log.json"

DISPATCH = {
    "growth_pct":         (m.growth_pct, ["closing", "opening"]),
    "stage3_pct":         (m.stage3_pct, ["stage3", "gross_loans"]),
    "stage2_pct":         (m.stage2_pct, ["stage2", "gross_loans"]),
    "write_off_rate":     (m.write_off_rate, ["writeoffs", "opening_stage3"]),
    "adjusted_gnpa":      (m.adjusted_gnpa, ["gnpa", "writeoffs", "loans"]),
    "provision_coverage": (m.provision_coverage, ["stage3_provisions", "stage3_gross"]),
    "credit_cost":        (m.credit_cost, ["impairment", "average_loans", "annualise"]),
    "cost_of_funds":      (m.cost_of_funds, ["interest_expense", "average_borrowings", "annualise"]),
    "share_pct":          (m.share_pct, ["part", "total"]),
    "ape":                (arch.ape, ["single_premium", "first_year_regular"]),
    "vnb_margin":         (arch.vnb_margin, ["vnb", "ape"]),
    "solvency_ratio":     (arch.solvency_ratio, ["available", "required"]),
    "loss_ratio":         (arch.loss_ratio, ["claims_incurred", "net_earned_premium"]),
    "combined_ratio":     (arch.combined_ratio, ["loss_ratio", "expense_ratio"]),
    "transaction_yield":  (arch.transaction_yield, ["charges", "turnover"]),
    "core_income":        (arch.core_income, ["transaction", "listing", "data"]),
    "amc_yield":          (arch.amc_yield, ["revenue", "average_aum"]),
    "net_flows":          (arch.net_flows_delta, ["closing_aum", "opening_aum", "market_appreciation"]),
    "qaaum_share":        (arch.qaaum_share, ["qaaum", "total_industry"]),
}
OPTIONAL = {"annualise"}


def _facts():
    p = DATA / "facts_company.json"
    return {f["id"]: f for f in json.loads(p.read_text(encoding="utf-8"))} if p.exists() else {}


def calculate(name, inputs, label=""):
    if name not in DISPATCH:
        raise ValueError(f"unknown formula: {name}. Known: {sorted(DISPATCH)}")
    fn, params = DISPATCH[name]
    facts, args, used = _facts(), {}, []
    for p in params:
        if p not in inputs:
            if p in OPTIONAL:
                continue
            raise ValueError(f"missing input '{p}' for {name}; needs {params}")
        v = inputs[p]
        if isinstance(v, str) and v in facts:
            used.append(v); v = facts[v]["value"]
        args[p] = float(v)
    value, formula = fn(**args)
    log = json.loads(CALC_LOG.read_text(encoding="utf-8")) if CALC_LOG.exists() else []
    cid = f"C{len(log) + 1:03d}"
    entry = {"id": cid, "name": name, "label": label, "formula": formula, "inputs": inputs,
             "fact_ids": used, "value": round(value, 4)}
    log.append(entry)
    CALC_LOG.write_text(json.dumps(log, indent=2, ensure_ascii=False), encoding="utf-8")
    return entry
