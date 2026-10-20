"""Offline tests for the code layer: formulas, peers, scoring patches, relationships, fact verification,
report building. No internet and no API key needed."""
import json, subprocess, sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import archetypes as arch
import metrics as m
import peers
import scoring


def test_finder_checks_pass():
    r = subprocess.run([sys.executable, "test_finder.py"], cwd=ROOT, capture_output=True, text=True, timeout=300,
                       stdin=subprocess.DEVNULL)
    assert r.returncode == 0, r.stdout + r.stderr
    assert "15 checks passed" in r.stdout


def test_group_company_is_not_the_company():
    """Found live on 20 Oct 2026: a search for Bajaj Finance returned Bajaj Housing Finance files."""
    import finder
    from finder import norm
    assert finder.sibling_word(norm("bajajhousingfinance.in investor presentation"), "Bajaj Finance") == "housing"
    assert finder.sibling_word(norm("bajaj-finance-q1-fy27-investor-presentation"), "Bajaj Finance") is None
    assert finder.sibling_word(norm("Bajaj Housing Finance"), "Bajaj Housing Finance") is None


def test_lender_formulas():
    assert m.stage3_pct(2, 100)[0] == pytest.approx(2.0)
    assert m.adjusted_gnpa(2, 1, 100)[0] == pytest.approx(3 / 101 * 100)
    assert m.growth_pct(120, 100)[0] == pytest.approx(20.0)
    with pytest.raises(ValueError):
        m.stage3_pct(1, 0)                       # DATA-CHECK-FAILED, never a silent divide


def test_archetype_formulas():
    assert arch.ape(1000, 200)[0] == pytest.approx(300.0)   # 10% of single + 100% of regular
    assert arch.vnb_margin(26, 100)[0] == pytest.approx(26.0)
    assert arch.transaction_yield(5, 10000)[0] == pytest.approx(5.0)
    d = arch.rupee_delta(2, 100, 3, 200)
    assert d["num_delta"] == 1 and d["ratio_new"] < d["ratio_old"]


def test_peer_selection_by_archetype_metric():
    co = {"name": "X", "advances": 100, "fiscal_end": "Mar"}
    cands = [{"name": "A", "advances": 50, "fiscal_end": "Mar"}, {"name": "B", "advances": 300, "fiscal_end": "Mar"},
             {"name": "C", "advances": 1000, "fiscal_end": "Mar"}]
    got, mode, key = peers.pick_peers(co, cands, "bank")
    assert key == "advances" and mode == "in-band" and [c["name"] for c in got] == ["A", "B"]


def _lead(**kw):
    t = {d: [True] * 5 for d in scoring.DIMS_V4}
    base = dict(independent_families=3, has_tier1_or_2=True, counter_categories_searched=5,
                falsification_criteria_met=5, confounders_checked=True, claims_verified=True, source_documents=3)
    base.update(kw)
    return scoring.Lead("L", "x", t, **base)


def test_moderate_counterargument_caps_label():          # runbook defect 1
    assert scoring.evidence_label(_lead(counter_strength="Weak")) == "Strong"
    assert scoring.evidence_label(_lead(counter_strength="Moderate")) == "Moderate"
    assert scoring.evidence_label(_lead(counter_strength="Moderate", counter_resolved=True)) == "Strong"


def test_agreement_rate_logged():                         # runbook defect 2
    log = []
    scoring.judged_pass([True, True, True], log)
    scoring.judged_pass([True, False, True], log)
    assert scoring.agreement_rate(log) == pytest.approx(0.5)


def test_noise_test_uses_scoring_rules():                 # runbook defect 3
    src = (ROOT / "noise_test.py").read_text(encoding="utf-8")
    assert "from scoring import MACHINE, JUDGED" in src and "MACHINE = {" not in src


def test_relationships_flag_and_not_testable():
    from agent import relationships
    f = lambda i, mt, v, p: {"id": i, "metric": mt, "value": v, "period": p, "scope": "consolidated"}
    facts = [f("F1", "aum", 100, "Q1 FY26"), f("F2", "aum", 110, "Q1 FY27"),
             f("F3", "stage3_amount", 2, "Q1 FY26"), f("F4", "stage3_amount", 2.6, "Q1 FY27")]
    res = relationships.evaluate(facts)
    edges = {e["id"]: e for e in res["edges"]}
    assert edges["R1"]["status"] == "FLAGGED"            # Stage 3 grew 30% vs AUM 10%
    assert edges["R5"]["status"] == "NOT-TESTABLE"
    assert len(edges) == 17


@pytest.fixture
def sandbox(tmp_path, monkeypatch):
    """Point the agent's data/output folders at a temp dir and make a small real PDF."""
    import agent
    from agent import tools_state, tools_calc, build_report, tools_web, tools_report
    for mod in (agent, tools_state, tools_calc, build_report, tools_web, tools_report):
        if hasattr(mod, "DATA"):
            monkeypatch.setattr(mod, "DATA", tmp_path / "data")
        if hasattr(mod, "OUT"):
            monkeypatch.setattr(mod, "OUT", tmp_path / "out")
    monkeypatch.setattr(tools_state, "FACTS", tmp_path / "data" / "facts_company.json")
    monkeypatch.setattr(tools_state, "LEADS", tmp_path / "data" / "leads.json")
    monkeypatch.setattr(tools_state, "CALC_LOG", tmp_path / "data" / "calc_log.json")
    monkeypatch.setattr(tools_calc, "CALC_LOG", tmp_path / "data" / "calc_log.json")
    tools_state.reset()
    from reportlab.pdfgen import canvas
    pdf = tmp_path / "deck.pdf"
    c = canvas.Canvas(str(pdf))
    c.drawString(72, 750, "Assets under management grew to Rs 4,41,450 crore as of 30 June 2026.")
    c.drawString(72, 730, "Gross Stage 3 assets stood at 1.31% of gross loans.")
    c.save()
    tools_web.DOCS.clear()
    tools_web.DOCS.append(dict(id="D01", file=str(pdf), url="https://example-company.in/deck.pdf", tier=2, family="A"))
    return tmp_path


def test_fact_verification_by_code(sandbox):
    from agent import tools_state
    out = tools_state.save_facts([
        {"metric": "aum", "value": 441450, "unit": "Rs crore", "period": "Q1 FY27", "scope": "consolidated",
         "doc": "D01", "page": "1", "excerpt": "Assets under management grew to Rs 4,41,450 crore"},
        {"metric": "stage3_pct", "value": 9.99, "unit": "%", "period": "Q1 FY27", "scope": "consolidated",
         "doc": "D01", "page": "1", "excerpt": "Gross Stage 3 assets stood at"},     # wrong number
    ])
    assert out[0]["verified"] is True
    assert out[1]["verified"] is False and "not found" in out[1]["note"]


def test_calc_from_fact_ids_and_report(sandbox):
    from agent import tools_state, tools_calc, tools_report
    tools_state.save_facts([{"metric": "aum", "value": 441450, "unit": "Rs crore", "period": "Q1 FY27",
                             "scope": "consolidated", "doc": "D01", "page": "1",
                             "excerpt": "Assets under management grew to Rs 4,41,450 crore"}])
    c = tools_calc.calculate("growth_pct", {"closing": "F001", "opening": 400000}, "AUM growth")
    assert c["fact_ids"] == ["F001"] and c["value"] == pytest.approx(10.3625)
    tools_state.save_lead({"id": "L1", "name": "test lead", "fact_ids": ["F001"], "calc_ids": [c["id"]],
                           "tests": {d: [True] * 5 for d in scoring.DIMS_V4}, "counter_categories_searched": 4,
                           "falsification_criteria_met": 4, "confounders_checked": True,
                           "counter_strength": "Weak", "is_company_headline": False})
    res = tools_state.score_leads()
    assert res["rows"][0]["gates_passed"] is False        # one family, one document: gates A and G fail
    assert "No Strong Finding" in res["verdict"]
    out = tools_report.write_report("both", {"discovery": "No Strong Finding."})
    assert Path(out["docx"]).exists() and Path(out["json"]).exists()
