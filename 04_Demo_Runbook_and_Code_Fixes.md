# Finals run-book, failure plan, Q&A prep and code patches

## 1. The 10-minute demo (brief p.108–109: 10 min presentation + demo, 15 min Q&A)

| Time | What happens | Why it wins marks |
|---|---|---|
| 0:00–0:25 | One sentence: "Everyone can summarise a filing. We test it." | Sets up discovery vs summary |
| 0:25–1:30 | Architecture slide: sources → provenance store → code metrics → relationships → leads → gates → one finding. Say the line: *"the AI never does arithmetic and never picks the winner; code does."* | Explainability + robustness |
| 1:30 | Judges name a company. Start the live run on screen. | Autonomy |
| 1:30–5:00 | Show the Coverage Log filling, facts landing with page numbers, **two blocked sources being logged honestly** | Judges reward honesty, not omniscience |
| 5:00–7:30 | Lead Register appears: 6–9 leads, gate results, failures named | Shows the agent rejected things |
| 7:30–9:00 | The Discovery, its three evidence families, the strongest counterargument with its rating | Falsifiability |
| 9:00–9:40 | Falsification condition, named checkpoint, threshold and its source | This is the element most teams omit |
| 9:40–10:00 | Limitations and coverage grade, stated without apology | Generality |

**Rule for the demo:** run in **express mode** so the Lead Register is visible at ~7 minutes. Say
plainly: "the full 30-minute run continues after this; express uses the same code path with fewer
documents." Do not pretend 30 minutes fits in 10.

## 2. Failure playbook (decide these before the finals, not during)

| Failure | Live behaviour |
|---|---|
| NSE/niftyindices unreachable (it timed out on 3 plain fetches during this review) | Fall back to a **dated local constituent file** + BSE links; print "index membership from cached list dated <date>" |
| Exchange site blocks the crawler | Retry twice with browser headers, then log `BLOCKED` and use the annual report on the company IR domain |
| Annual report is scanned | OCR, mark figures `OCR-UNCERTAIN`, cross-check one figure against the results filing; if no cross-check, drop the metric |
| Table extraction gives inconsistent totals | G13 fires `DATA-CHECK-FAILED`; drop the number, keep the lead only if another family supports it |
| No lead passes the gates | Report **No Strong Finding** with the Lead Register. Rehearse saying this — it is a strength, and judges test whether you can resist inventing a story |
| Wi-Fi fails entirely | Pre-cache two companies' documents; run offline and show the identical output |

## 3. Q&A bank (15 minutes is long — prepare depth, not defence)

1. *"Isn't this just an LLM with a long prompt?"* → "The prompt is the specification. The gates, scoring,
   peer selection and every calculation are Python; the model cannot award itself a point."
2. *"How do you stop hallucinated numbers?"* → Provenance record per datum, extraction must cite page and
   excerpt, verification pass re-reads the excerpt, and any pass without an evidence id counts as a fail.
3. *"What if the judges pick a life insurer?"* → Show §8B: APE, VNB margin, persistency, solvency are
   fixed formulas; the agent classifies the archetype first and fills the same nine slots.
4. *"What if they pick an unlisted company?"* → §15A: look through to a listed parent, else MCA/DRHP with
   LIMITED coverage; never infer numbers from news.
5. *"How is this not hard-coded?"* → No company names, thresholds or peers in the code; peers come from a
   size band on an archetype-specific metric; thresholds come from the company's own history or peers.
6. *"Why should we trust the ranking?"* → 30 binary tests, 18 machine-checked from logs, 12 judged by three
   independent passes with majority rule; 94.5% top-lead stability at 10% rater noise.
7. *"What did you get wrong?"* → Have one honest answer ready (e.g. the v5 archetype points were judgement,
   not measured; BSE Ltd's index entry was unconfirmed at the time and is now confirmed).
8. *"Where is the falsification condition?"* → Point at the dated checkpoint and the threshold's source.

## 4. Code patches (three real defects in `scoring.py`)

**Defect 1 — `counter_strength` is dead code.** The spec (§12.3) says an unresolved *Moderate*
counterargument caps the label at Moderate and an unresolved *Strong* one caps it at Weak. `capped()` only
reads `unresolved_strong_counter`, so a Moderate counterargument has no effect at all.

```python
# 1) add the field to Lead
    counter_strength: str = "Weak"
    counter_resolved: bool = False          # NEW: answered with evidence?

# 2) replace residual()
def residual(l: Lead) -> str:
    if l.unresolved_strong_counter: return "Weak"
    if not l.counter_resolved and l.counter_strength == "Strong":  return "Weak"
    if not l.counter_resolved and l.counter_strength == "Moderate": return "Moderate"
    return "Moderate" if l.tests["robustness"][2] else "Weak"

# 3) in evidence_label(), after the existing unresolved-strong line
    elif not l.counter_resolved and l.counter_strength == "Moderate" and label == "Strong":
        label = "Moderate"
```

**Defect 2 — the 80% agreement rule is never computed.** §12.0 requires logging the three-rater agreement
rate and flagging the run below 80%.

```python
def judged_pass(votes, log=None):
    assert len(votes) == 3
    if log is not None:
        log.append(1.0 if all(votes) or not any(votes) else 0.0)   # 1 = all three agreed
    return sum(bool(v) for v in votes) >= 2

def agreement_rate(log) -> float:
    return (sum(log) / len(log)) if log else 1.0        # flag the run if < 0.80
```

**Defect 3 — `MACHINE` is duplicated** in `scoring.py` and `noise_test.py`. Two copies will drift; the
noise test would then validate a different rule set from the one that scores. In `noise_test.py` delete
lines 5–7 and add `from scoring import MACHINE, JUDGED`.

## 5. Drop-in modules that close the feasibility gap

`metrics.py` — the formulas the prompt says must exist (patch P1). Pure functions, no I/O, no AI.

```python
"""Archetype metric formulas. Every function returns (value, formula). ValueError = DATA-CHECK-FAILED."""
def _pos(x, name):
    if x is None or x <= 0: raise ValueError(f"{name} must be positive, got {x}")
    return float(x)

def stage3_pct(stage3, gross_loans):
    g = _pos(gross_loans, "gross_loans"); return stage3 / g * 100, "stage3 / gross_loans * 100"

def write_off_rate(writeoffs, opening_stage3):
    return writeoffs / _pos(opening_stage3, "opening_stage3") * 100, "writeoffs / opening_stage3 * 100"

def adjusted_gnpa(gnpa, writeoffs, loans):
    l = _pos(loans, "loans"); return (gnpa + writeoffs) / (l + writeoffs) * 100, \
        "(gnpa + writeoffs) / (loans + writeoffs) * 100"

def vnb_margin(vnb, ape):
    return vnb / _pos(ape, "ape") * 100, "vnb / ape * 100"

def solvency(available, required, minimum=1.5):
    r = _pos(required, "required"); return available / r, f"available / required (min {minimum})"

def loss_ratio(claims, net_earned_premium):
    return claims / _pos(net_earned_premium, "nep") * 100, "claims / nep * 100"

def transaction_yield(charges, turnover):
    """Basis points. Exchange archetype (BSE Ltd)."""
    return charges / _pos(turnover, "turnover") * 10000, "charges / turnover * 10000 (bps)"

def amc_yield(revenue, average_aum):
    return revenue / _pos(average_aum, "average_aum") * 10000, "revenue / average_aum * 10000 (bps)"

def rupee_delta(old_num, old_den, new_num, new_den):
    """G14: never report a ratio move without the underlying amount move."""
    return {"num_delta": new_num - old_num, "den_delta": new_den - old_den,
            "ratio_old": old_num / _pos(old_den, "old_den"),
            "ratio_new": new_num / _pos(new_den, "new_den")}
```

`peers.py` — the archetype-aware peer rule (patch P2), replacing the AUM-only rule.

```python
SCALE = {"bank": "advances", "nbfc": "aum", "hfc": "aum", "life": "ape",
         "general": "gwp", "amc": "aum", "exchange": "revenue", "holding": "cons_assets"}

def pick_peers(company, candidates, archetype, band=(0.25, 4.0), n=3):
    """Same archetype, same fiscal calendar, size within band of the archetype's scale metric.
    Falls back to the closest n by that metric and flags the substitution."""
    key = SCALE[archetype]
    base = float(company[key])
    inside = [c for c in candidates
              if c.get("fiscal_end") == company.get("fiscal_end")
              and band[0] * base <= float(c[key]) <= band[1] * base]
    if len(inside) >= 2:
        return inside[:n], "in-band", key
    closest = sorted(candidates, key=lambda c: abs(float(c[key]) / base - 1.0))[:n]
    return closest, "out-of-band: trends only", key
```

Both modules take plain dicts/scalars, so they can be unit-tested without any model call — which is the
point: the arithmetic layer must be verifiable independently of the AI.

## 6. Order of work (what to do, in what order, from now)

| When | Do | Why |
|---|---|---|
| Tonight | The 1-page submission (file 03); apply P4 and P5 (one rubric, ten run-QC items) | Round 1 closes today |
| Tonight | Add the applicability table (file 02) to the submission | Directly answers the generality criterion |
| 20 Oct | Apply P1 (archetype formulas), P2 (peers), P3 (unlisted), P6 (budget) | Removes the "invents formulas at run time" hole |
| 20–21 Oct | Drop in `metrics.py` and `peers.py`; apply the three `scoring.py` patches; re-run `run_tests.py` and `noise_test.py` | Proves the gates still hold after the changes |
| 21–22 Oct | One full run on a company you did not design around (Muthoot or Bank of Baroda); paste the Coverage Log into the finals deck | Converts your own f5 from 0 → 2 |
| 23–24 Oct | Rehearse the 10-minute demo three times, including one deliberate failure | The demo, not the prompt, decides the finals |
| 25 Oct | Run express mode live; full report completes after | Matches the brief's 10-minute format |
