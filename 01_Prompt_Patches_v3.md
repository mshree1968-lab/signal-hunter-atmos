# Track A Master Prompt — v3 patch set

Apply in order to `Track_A_Agent_Master_Prompt_v2.md`. Each patch names the section to replace.
P1–P3 close the feasibility gaps; P4–P6 the clarity gaps; P7 adds the output contract.

---

## P1. Replace the final paragraph of §8A

Find the paragraph beginning **"Section 9 and Section 10 are the lender module."** and replace it
with everything below.

### §8B Archetype modules (formulas are fixed here, never invented at run time)

You may apply **only** the formulas in this section to non-lender archetypes. If an input is
missing, mark the slot `NOT-TESTABLE`, log it in the Coverage Log, and continue. Inventing a
formula at run time breaches G3 (arithmetic in code) and G8 (no ad-hoc definitions).

**Life insurer (HDFC Life, SBI Life, ICICI Pru Life)**
- APE = 0.5 × single premium + 1.0 × first-year regular premium. Record the company's own definition.
- VNB margin = VNB ÷ APE. Protection share = protection APE ÷ APE.
- Persistency 13m / 25m / 61m as reported. Surrender ratio = surrenders ÷ average policies in force.
- Solvency ratio = available solvency margin ÷ required (regulatory minimum 150%).
- Commission + opex ratio = (commission + operating expenses) ÷ GWP. EV and operating variance as disclosed.
- U1: APE growth vs 13m persistency and surrenders. U2: VNB vs PAT (VNB can exceed PAT by design;
  flag only the *direction and size of change*, never the level). U3: solvency vs 150% and vs capital
  raised. U4: investment portfolio quality and liquidity. U9: channel mix, especially bancassurance
  dependence on the parent bank.
- Tier 1 sources: IRDAI public disclosures (mandatory, quarterly), annual report, EV disclosure.
- Falsification thresholds in ₹ crore or percentage points, never in a ratio whose denominator moves.

**General insurer (ICICI Lombard)**
- GWP growth; loss ratio = claims incurred ÷ net earned premium; expense ratio; combined ratio.
- Reserve development = prior-year reserve releases ÷ PBT. Investment leverage = investments ÷ net worth.
- U2 flag: PBT grows faster than the underwriting result, driven by reserve releases or investment gains.
- U9: line-of-business and channel concentration; reinsurance dependence.

**Exchange (BSE Ltd — NIFTY 50 member since 30 September 2026)**
- Revenue split: transaction charges, listing, data, other. Transaction yield = transaction charges ÷
  turnover, in basis points. Core income = transaction + listing + data.
- U1: turnover growth vs transaction yield (flag when volumes rise while the take-rate falls sharply —
  price-led volume, the same logic as the brief's Track C example).
- U2: core vs treasury/other income. U3: net worth and settlement guarantee fund.
- U9: product and client concentration; dependence on one segment (e.g. derivatives) and on SEBI fee rules.
- U4 is not applicable — mark it, do not invent a funding metric. Peer: MCX (listed); NSE is unlisted,
  so use it only for market-share context and mark it Tier 2.

**Asset manager (HDFC AMC, Nippon, UTI)**
- QAAUM and average AUM; net flows vs market appreciation; market share; yield = revenue ÷ average AUM
  (bps); operating margin; cost-to-income; SIP book; scheme concentration; TER regime changes.
- U1 flag: AUM grows while net flows are negative (growth is beta, not franchise).

**Holding company (Bajaj Finserv)**
- Report standalone and consolidated separately. Look-through contribution: each subsidiary's share of
  consolidated profit; stake percentages; upstream dividends; standalone net worth and holding debt;
  interest cover at the parent.
- U1: subsidiary growth vs subsidiary asset quality (run the lender module on the lending subsidiary).
- U2: contribution by subsidiary. U3: standalone vs consolidated net worth. U9: share of profit from the
  largest subsidiary. Do not apply NBFC ratios to the parent's consolidated total.

**Newly demerged / short-history entity (Jio Financial Services)**
- Run in LIMITED mode unless five years can be reconstructed from parent filings. Say which years are
  reconstructed and from which document.

---

## P2. Replace the peer-selection rule in §8

Find **"Peer selection rule (no hand-picking): ... AUM between roughly 0.25x and 4x"** and replace with:

> **Peer selection rule (no hand-picking):** 2 to 3 listed companies of the same archetype and primary
> business model, same fiscal calendar, with size between 0.25x and 4x of the company's **primary scale
> metric for that archetype**: advances (banks), AUM (NBFC/HFC/AMC), APE (life insurers), GWP (general
> insurers), revenue (exchanges), consolidated assets (holding companies). State the metric used. If no
> peer falls inside the band, use the closest 2 by that metric and compare **trends, not levels**.

---

## P3. Add §15A Unlisted and unresolvable entities

> **§15A Unlisted or unresolvable entity.** If the entity is not listed on NSE/BSE:
> (a) check whether it is a subsidiary of a listed parent — if so, analyse the parent's consolidated
> filings, state the look-through basis, and continue;
> (b) otherwise state plainly that no Tier 1 or Tier 2 periodic disclosure exists, restrict to MCA
> AOC-4, charge records and any DRHP, mark the run LIMITED, and produce the eight elements only if two
> independent families exist;
> (c) never build a number from news alone. If the name cannot be resolved to a listed entity after two
> searches, stop and say so — do not guess a ticker.

---

## P4. One scoring system only

Delete §12.2 (the second Evidence Strength definition). Keep §3.7 as the only label rule and §12.0 as
the only score. Add this line at the top of §12: *"This is the only rubric in force. If any other
document in the pack defines a different scale or label, this section wins."*

## P5. Make the run-level grade cover the judges' full criteria

Replace §14.4's eight items with these ten (A = 10, B = 8–9, C = below 8):

1. eight elements complete; 2. every number has a source tag; 3. terms defined in plain language;
4. calculation log present; 5. verification pass done; 6. same checks run on peers;
7. applicability and limitations stated; 8. coverage grade stated;
**9. explainability: a human can trace every claim to its source in three steps or fewer;**
**10. autonomy: the run log shows zero human edits or hints during the run.**

## P6. Budget the run (add to §11, after the stop rules)

| Item | Full mode cap | Express cap |
|---|---|---|
| URLs fetched | 25 | 10 |
| Documents parsed | 15 | 6 |
| Retries per blocked source | 2 | 1 |
| Judged scoring: leads scored with 3 rater passes | **top 3 only** | top 2 only |
| Model calls (target) | ≤ 120 | ≤ 45 |
| Wall clock | 30 min | 10 min |

Rationale: scoring 8 leads with 3 passes costs ~290 calls; capping judged scoring to the top 3 costs
~108 and changes no ranking, because the hard gates already remove the weak leads.

## P7. Output contract (§14, after the JSON sentence)

```json
{"run":{"company":"","entity_scope":"standalone|consolidated","as_of":"","mode":"","peers":[],
        "run_grade":"","coverage_grade":"","archetype":""},
 "discovery":{"sentence":"","why_it_matters":[""],"evidence_strength":"","reasoning_rating":""},
 "evidence":[{"id":"E1","family":"A-F","tier":1,"title":"","date":"","page":"","url":"",
              "excerpt":"","rating":""}],
 "timeline":[{"date":"","event":"","fact_id":""}],
 "numbers":[{"metric":"","period":"","value":0,"unit":"","formula":"","inputs":["F1"],"calc_id":""}],
 "counterargument":{"strongest":"","evidence_ids":[],"rating":"","explains":"","residual":""},
 "falsification":{"condition":"","checkpoint":"","threshold":"","threshold_source":"","rating":""},
 "leads":[{"id":"","description":"","score":0,"gates_passed":true,"outcome":"",
           "evidence_label":"","why_not_chosen":""}],
 "relationships":[{"id":"R1","status":"CLEAN|FLAGGED|NOT-TESTABLE","company":"","peers":""}],
 "sources":[{"id":"S1","title":"","tier":1,"url":"","status":"read|blocked|not_found"}],
 "verification":[{"claim_id":"","result":"supported|downgraded|removed","note":""}],
 "checkpoints":[{"date":"","event":""}]}
```

Every `numbers[].inputs` entry must resolve to a fact id, and every `evidence[].id` must be cited by at
least one lead or by the discovery. A dashboard may rely on this contract; do not add keys silently.

