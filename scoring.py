"""
Track A lead-scoring module (v4).
Design: gates first, then binary checklists (each pass needs an evidence id),
then caps, then outcome. Labels are derived by rule from the checklist results.
The AI only answers pass/fail + evidence ids; this code does all arithmetic.
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---- v4 lead-score dimensions (sum = 100). Each has exactly 5 binary tests. ----
DIMS_V4 = {"discovery": 22, "evidence": 18, "cross_source": 12,
           "temporal": 12, "falsifiability": 18, "robustness": 18}
# ---- v3 (earlier draft) kept only so the tests can compare versions ----
DIMS_V3 = {"discovery": 20, "evidence": 15, "cross_source": 10, "temporal": 10,
           "falsifiability": 15, "robustness": 15, "explainability": 10, "generality": 5}

TESTS = {
 "discovery": ["not_company_headline", "not_stated_by_3plus_retrieved_items",
               "needs_2plus_documents", "needs_derived_calculation",
               "qualifies_or_contradicts_claim_or_summary_metric"],
 "evidence": ["tier1_supports_core_fact", "derived_numbers_reproduced_in_code",
              "claims_verified_vs_excerpt", "no_unresolved_conflict",
              "definitions_scope_consistent"],
 "cross_source": ["two_plus_independent_families", "three_plus_families",
                  "independent_family_confirms_direction", "two_plus_peers_checked",
                  "sector_or_regulator_benchmark_checked"],
 "temporal": ["four_plus_periods", "onset_dated_with_source", "yoy_and_qoq_checked",
              "pre_onset_baseline", "trigger_event_identified_or_none_found_stated"],
 "falsifiability": ["linked_to_finding", "measurable_and_public", "dated_checkpoint",
                    "threshold_from_history_peers_or_guidance", "can_fail_both_ways_unconfounded"],
 "robustness": ["four_plus_counter_categories_searched", "strongest_counter_identified_with_evidence",
                "residual_finding_at_least_moderate", "confounders_adjusted",
                "survives_peer_or_sector_adjustment"],
 # v3-only dimensions (shown to be non-discriminating; moved to run-level QC in v4)
 "explainability": ["one_sentence_45_words", "every_number_sourced", "chain_5_steps_or_less",
                    "timeline_present", "terms_defined"],
 "generality": ["from_universal_relationship", "no_company_specific_threshold",
                "standard_public_docs_only", "same_check_run_on_peer", "applicability_stated"],
}

@dataclass
class Lead:
    id: str
    name: str
    tests: Dict[str, List[bool]]              # dimension -> 5 booleans
    evidence_ids: Dict[str, List[List[str]]] = field(default_factory=dict)
    # gate inputs
    independent_families: int = 0
    has_tier1_or_2: bool = False
    counter_categories_searched: int = 0
    falsification_criteria_met: int = 0
    confounders_checked: bool = False
    claims_verified: bool = False
    source_documents: int = 0
    # cap inputs
    unresolved_strong_counter: bool = False
    unresolved_conflict: bool = False
    counter_strength: str = "Weak"            # Strong/Moderate/Weak (threat to finding)
    counter_resolved: bool = False            # NEW: answered with evidence?
    is_company_headline: bool = False

def validate(lead: Lead, strict=True):
    for d, vals in lead.tests.items():
        assert len(vals) == 5, f"{lead.id}/{d}: need 5 tests"
        if strict:
            ev = lead.evidence_ids.get(d, [[]]*5)
            for i, v in enumerate(vals):
                if v and not ev[i]:
                    raise ValueError(f"{lead.id}/{d}/{TESTS[d][i]}: pass without evidence id")

def gates(l: Lead) -> Dict[str, bool]:
    return {
     "A_two_independent_families_incl_tier1or2": l.independent_families >= 2 and l.has_tier1_or_2,
     "B_derived_numbers_reproduced": l.tests["evidence"][1],
     "C_four_counter_categories": l.counter_categories_searched >= 4,
     "D_falsification_4_of_5": l.falsification_criteria_met >= 4,
     "E_confounders_checked": l.confounders_checked,
     "F_claims_verified": l.claims_verified,
     "G_not_single_document": l.source_documents >= 2,
     "H_not_company_headline": not l.is_company_headline,
    }

def raw_score(l: Lead, dims: Dict[str, int]) -> float:
    return sum(sum(l.tests[d]) / 5 * w for d, w in dims.items())

def capped(l: Lead, s: float):
    cap, why = 100, []
    if l.unresolved_strong_counter: cap = min(cap, 59); why.append("unresolved strong counterargument (cap 59)")
    if l.unresolved_conflict:       cap = min(cap, 79); why.append("unresolved source conflict (cap 79)")
    return min(s, cap), why

def outcome(s: float) -> str:
    return ("Strong candidate" if s >= 80 else "Moderate" if s >= 65 else
            "Weak" if s >= 50 else "No strong finding")

def residual(l: Lead) -> str:
    if l.unresolved_strong_counter:
        return "Weak"
    if not l.counter_resolved and l.counter_strength == "Strong":
        return "Weak"
    if not l.counter_resolved and l.counter_strength == "Moderate":
        return "Moderate"
    return "Moderate" if l.tests["robustness"][2] else "Weak"

def evidence_label(l: Lead) -> str:
    """Derived by rule, not by score."""
    e, c = l.tests["evidence"], l.tests["cross_source"]
    strong = all(e[:4]) and c[0] and c[2] and c[3] and residual(l) != "Weak" and not l.unresolved_conflict
    moderate = c[0] and (e[0] or e[2]) and residual(l) != "Weak"
    label = "Strong" if strong else "Moderate" if moderate else "Weak"
    if l.unresolved_strong_counter: label = "Weak"
    elif not l.counter_resolved and l.counter_strength == "Moderate" and label == "Strong":
        label = "Moderate"
    return label

def score_all(leads: List[Lead], dims=DIMS_V4):
    rows = []
    for l in leads:
        g = gates(l); s0 = raw_score(l, dims); s, why = capped(l, s0)
        rows.append(dict(id=l.id, name=l.name, raw=round(s0, 1), final=round(s, 1),
                         gates_passed=all(g.values()), failed=[k for k, v in g.items() if not v],
                         caps=why, outcome=outcome(s), evidence_label=evidence_label(l)))
    rows.sort(key=lambda r: (r["gates_passed"], r["final"]), reverse=True)
    top = [r for r in rows if r["gates_passed"]]
    close = len(top) >= 2 and abs(top[0]["final"] - top[1]["final"]) <= 5
    return rows, ("close call" if close else "clear leader" if top else "no lead passed all gates")

# ---- Run-level quality control (replaces the non-discriminating v3 dimensions) ----
RUN_QC = ["eight_elements_complete", "every_number_has_source_tag", "terms_defined_plain_language",
          "calculation_log_present", "verification_pass_done", "same_checks_run_on_peers",
          "applicability_and_limitations_stated", "coverage_grade_stated"]
def run_grade(passed: Dict[str, bool]) -> str:
    n = sum(passed.get(k, False) for k in RUN_QC)
    return "A" if n == 8 else "B" if n >= 6 else "C"

# ---- v5 reliability rules (found necessary by the noise test) ----
# Machine-checked tests are computed from logs by code (counts, tiers, calc log, dates): never AI-judged.
MACHINE = {"discovery": [1, 2, 3], "evidence": [0, 1, 2, 3], "cross_source": [0, 1, 3, 4],
           "temporal": [0, 2, 3], "falsifiability": [2, 3], "robustness": [0, 4]}
JUDGED = {d: [i for i in range(5) if i not in MACHINE[d]] for d in MACHINE}

def judged_pass(votes, log=None):
    """Judged tests: three independent rater passes (different prompts or seeds); majority wins.
    Every pass still needs an evidence id. Log the agreement rate; below 80% flags the run."""
    assert len(votes) == 3
    if log is not None:
        log.append(1.0 if all(votes) or not any(votes) else 0.0)   # 1 = all three agreed
    return sum(bool(v) for v in votes) >= 2

def agreement_rate(log) -> float:
    """Share of judged tests where all three raters agreed. Below 0.80 flags the run."""
    return (sum(log) / len(log)) if log else 1.0

# ---- Viability gate by archetype (see spec): FULL needs >=12/18 slot points and U1, U2, U8 >= 1 ----
def viability(slot_points):
    total = sum(slot_points)
    must = slot_points[0] >= 1 and slot_points[1] >= 1 and slot_points[7] >= 1
    return ("FULL" if total >= 12 and must else "LIMITED"), total
