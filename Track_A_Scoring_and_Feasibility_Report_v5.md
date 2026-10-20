# Track A Scoring, Feasibility and Test Report (v5)

**Scope:** the lead-scoring system for the Track A agent, tested for clarity, feasibility and structure.
**Companion files:** `scoring_code/scoring.py`, `run_tests.py`, `noise_test.py` (all results below come from running these).

---

## 1. Verdict in one table

I replaced my earlier holistic "6 out of 10" with a **checkable rubric**: 15 yes/no checks, two points each. Anyone can verify each check in the files.

| Lens | Checks (2 points each) | v2 (previous) | v3 (first redesign) | **v5 (final)** |
|---|---|---|---|---|
| **Clarity** | c1 one-sentence description of system and output; c2 inputs, outputs and fields defined; c3 every threshold has a stated basis or is labelled heuristic; c4 output maps 1:1 to the brief's eight elements plus ratings; c5 worked end-to-end example on real data | 6 | 10 | **10** |
| **Feasibility** | f1 covers every Track A NIFTY 50 archetype; f2 covers non-NIFTY Track A archetypes; f3 free public sources only; f4 fallback modes and time budget; f5 tested end to end on real data for 3 or more archetypes | 2 | 8 | **8** |
| **Structure** | s1 fixed schema for every field; s2 deterministic scoring in tested code; s3 hard gates before scores; s4 one label system derived by rule; s5 reproducibility (top lead stable at least 90% at 10% rater noise, and at least 95% under weight changes) | 4 | 8 | **10** |
| **Average** | | **4.0** | **8.7** | **9.3** |

**Why v5 is not 10 on feasibility:** check f5 needs the agent run end to end on at least three archetypes. I spot-checked data availability for a bank, a life insurer and an NBFC and scored leads on real Bajaj Finance evidence, but I have not run a live agent. You will earn that last 2 points by running it.

**Caveat:** I wrote the rubric and I scored my own work. The judges' real rubric is not public in what I have seen. Treat the numbers as a disciplined self-audit, not a prediction of the judges' marks.

---

## 2. What the tests found, and what I changed

| # | Finding from testing | Fix in v5 |
|---|---|---|
| 1 | **The design was lending-only.** Track A's NIFTY 50 universe also contains insurers, a holding company, a newly demerged lender, and (per some sources) an exchange. Loan metrics do not apply to them. | Universal layer (U1 to U9) plus archetype modules and a viability gate (Section 3.1 to 3.2) |
| 2 | **Two scoring dimensions did not discriminate.** Explainability varied by only 2 points across leads and generality by only 1, so 15 weight points were wasted. | Moved both to a **run-level quality check** (Section 3.8) |
| 3 | **Ranking was fragile.** With every answer judged by the AI, the top lead held in only 69% of runs at 10% rater noise. | Split tests into machine-checked (18 of 30) and judged (12 of 30); judged tests use **3 rater passes, majority wins** |
| 4 | **The gate on code-reproduced numbers failed every lead** when evidence was gathered by hand. Correct behaviour: it proves the gate is real. | Kept. The agent must run calculations in code |
| 5 | **Double-scoring with AND did not help** (79.7% at 10% noise): it turned correct passes into fails. | Rejected. Majority-of-3 adopted instead |
| 6 | **Only 2 of 8 leads passed all gates**, because most had fewer than four counterargument categories searched. | Kept, and the agent's workflow now forces a search of every category for the top 2 leads |
| 7 | **Rating labels could conflict with numeric scores.** | One label system, derived by rule from checklist results (Section 3.7) |

---

## 3. The v5 system

### 3.1 Universal layer and archetype modules

The agent decides the company's **archetype**, then fills nine universal slots with that archetype's metrics. The relationship engine, scoring, gates and output are identical for all.

| Slot | Bank | NBFC / lender | Life insurer | General insurer | Exchange | Asset manager | Holding company |
|---|---|---|---|---|---|---|---|
| **U1 growth vs quality** | Advances growth vs GNPA rupees, slippages, SMA | AUM growth vs Stage 2 and 3 rupees | APE and VNB growth vs 13 and 61-month persistency, surrenders | Premium growth vs claims and combined ratio, reserve development | Turnover growth vs revenue per unit, product mix | AUM growth vs net flows | Subsidiary growth vs subsidiary quality |
| **U2 profit quality** | Pre-provision profit vs provisions vs one-offs | Pre-provision profit vs credit cost vs overlays | VNB and embedded value vs reported profit | Underwriting vs investment income | Core vs treasury income | Fee yield vs other income | Contribution by subsidiary |
| **U3 capital buffer** | CRAR, CET1 | CRAR, leverage | Solvency ratio vs minimum | Solvency ratio | Net worth, settlement guarantee fund | Net worth | Standalone vs consolidated |
| **U4 funding / liquidity / float** | CASA, deposits, LCR | Funding mix, ALM, LCR | Investment portfolio and liquidity | Reinsurance dependence | n/a | n/a | Upstream dividends, holding debt |
| **U5 claims vs delivery** | Guidance vs later actuals (all archetypes) | | | | | | |
| **U6 definition and policy changes** | Restated KPIs, accounting policy, presentation changes (all archetypes) | | | | | | |
| **U7 governance and ownership** | Auditor, management, pledge, regulator actions, related parties, parent dependence (all archetypes) | | | | | | |
| **U8 peers and independent source** | Peers, RBI data | Peers, rating rationale | Peers, IRDAI data | Peers, IRDAI data | SEBI data | AMFI data | Subsidiaries' peers |
| **U9 concentration** | Top exposures, sectors | Segment share of bad loans vs AUM, lender concentration | Channel (bancassurance) dependence, product mix | Line and channel mix | Product and client concentration | Scheme concentration | Share of profit from the largest subsidiary |

The 17 relationships (R1 to R17) in the master prompt are the **lender module**. Other archetypes get equivalent relationships from the table above.

### 3.2 Viability gate and modes

Each archetype scores 0, 1 or 2 per slot (2 = standard public Tier 1 or 2 data, 1 = partial or needs adaptation, 0 = not applicable or unavailable).
- **FULL mode:** at least 12 of 18 points **and** U1, U2 and U8 at least 1.
- **LIMITED mode:** otherwise. The agent still produces all eight elements, states reduced coverage, and rates evidence no higher than Moderate.
- **Express mode** (about 10 minutes): core metrics only.

### 3.3 Hard gates (pass or fail; a lead that fails any gate cannot be "The Discovery")

| Gate | Rule | Checked by |
|---|---|---|
| A | At least 2 independent source families, at least one Tier 1 or 2 | Code |
| B | Derived numbers reproduced in code | Code |
| C | At least 4 of 6 counterargument categories searched | Code (log count) |
| D | Falsification meets at least 4 of 5 criteria | Code and judged |
| E | Confounders checked (denominator, write-offs and one-offs, mix) | Judged |
| F | Every claim verified against its saved excerpt | Code |
| G | At least 2 source documents | Code |
| H | Not the company's own headline conclusion | Judged |

### 3.4 Lead score (100 points; six dimensions, five yes/no tests each)

| Dimension (points) | Tests |
|---|---|
| **Discovery and novelty (22)** | not the company's headline*; not stated by 3 or more retrieved items (M); needs 2 or more documents (M); needs a derived calculation (M); qualifies or contradicts a claim or summary metric* |
| **Evidence quality (18)** | Tier 1 source supports core fact (M); derived numbers reproduced in code (M); claims verified against excerpts (M); no unresolved conflict (M); definitions and scope consistent* |
| **Cross-source reasoning (12)** | 2 or more independent families (M); 3 or more families (M); an independent family confirms the direction*; 2 or more peers checked (M); sector or regulator benchmark checked (M) |
| **Temporal reasoning (12)** | 4 or more periods (M); onset dated with a source*; year-on-year and quarter-on-quarter checked (M); pre-onset baseline (M); trigger event identified, or "none found" stated* |
| **Falsifiability (18)** | linked to the finding*; measurable and public*; dated checkpoint (M); threshold from history, peers or guidance (M); can fail both ways and is not confounded* |
| **Robustness (18)** | 4 or more counterargument categories searched (M); strongest counterargument identified with evidence*; residual finding at least Moderate*; confounders adjusted*; survives peer or sector adjustment (M) |

(M) = machine-checked from logs. * = judged. Every pass needs an evidence id; a pass without one counts as a fail. Each test is worth dimension points ÷ 5.

**Judged tests:** three independent rater passes (different prompts or seeds), majority wins. Log the agreement rate; below 80% flags the run.

### 3.5 Caps and outcomes

- **Caps:** unresolved strong counterargument caps the lead at 59; unresolved source conflict caps it at 79.
- **Bands:** 80 or more = strong candidate; 65 to 79 = moderate; 50 to 64 = weak; below 50 = "No Strong Finding".
- **Close call:** if the top two gate-passing leads are within 5 points, report both.
- **Significance** (size and direction of the affected amount relative to its natural base) is **not scored**. It appears in "Why It Matters" and breaks ties only. No "Critical" or "High" wording, to stay clear of the no-recommendation rule.

### 3.6 Counterargument and falsification ratings
Unchanged from the master prompt (Section 12.3 and 12.4). Falsification must use rupee or amount thresholds, not ratios, whenever a denominator effect is possible.

### 3.7 Evidence Strength label (derived by rule, not from the score)
- **Strong:** Tier 1 source, derived numbers in code, claims verified, no unresolved conflict, 2 or more independent families with confirming direction, peers checked, residual finding at least Moderate.
- **Moderate:** 2 or more independent families, at least one of Tier 1 or verified claims, residual at least Moderate.
- **Weak:** anything else. An unresolved strong counterargument forces Weak.

### 3.8 Run-level quality check (grade A, B or C for the whole report)
Eight yes/no items: eight elements complete; every number has a source tag; terms defined in plain language; calculation log present; verification pass done; same checks run on peers; applicability and limitations stated; coverage grade stated. 8 = A, 6 to 7 = B, below 6 = C.

---

## 4. Test results

### 4.1 The Track A universe (as of October 2026; verify at niftyindices.com)
- **NIFTY 50, financial services (11 in September 2026 listings):** Axis Bank, HDFC Bank, ICICI Bank, Kotak Mahindra Bank, State Bank of India (banks); Bajaj Finance, Shriram Finance, Jio Financial Services (lenders); Bajaj Finserv (holding company); HDFC Life, SBI Life (insurers).
- **Possible addition:** one source lists BSE Ltd (an exchange) as added around 30 September 2026. I could not confirm this, so the agent must read the index list at run time and never hard-code it.
- **Same sector, outside the NIFTY 50 (tie-break candidates):** Cholamandalam, Muthoot Finance, Tata Capital, Power Finance Corporation, REC, IRFC, HDFC AMC, Bank of Baroda, Canara Bank, Punjab National Bank, Union Bank, and others.

**Implication:** the same code must handle at least seven archetypes, so the lender-only metric library was not enough.

### 4.2 Archetype viability (my assessment; spot-checks in 4.3)

| Archetype | Slot points | Mode |
|---|---|---|
| Private bank (HDFC, ICICI, Axis, Kotak) | 18 / 18 | FULL |
| NBFC retail lender (Bajaj Finance, Shriram, Cholamandalam, Muthoot) | 18 / 18 | FULL |
| Card or specialty lender (SBI Cards) | 18 / 18 | FULL |
| Life insurer (HDFC Life, SBI Life) | 17 / 18 | FULL |
| General insurer (ICICI Lombard) | 16 / 18 | FULL |
| Government lender (PFC, REC, IRFC) | 16 / 18 | FULL |
| PSU bank (SBI and others) | 15 / 18 | FULL |
| Small finance bank / housing finance company | 15 / 18 | FULL |
| Holding company (Bajaj Finserv) | 14 / 18 | FULL |
| Asset manager (HDFC AMC) | 14 / 18 | FULL (no U4) |
| Exchange (BSE) | 12 / 18 | FULL, at the threshold (no U4) |
| **Newly demerged lender (Jio Financial)** | **11 / 18** | **LIMITED** (short history, less than five years, thin disclosure) |

These slot points are my judgement of typical public disclosure, not measured values. Spot-checks below confirm three of them.

### 4.3 Spot-checks on real public data (data availability, not a full analysis)

- **Bajaj Finance (NBFC):** full test done in our earlier work: stage data, write-offs, funding mix, rating rationales, peers all found.
- **HDFC Bank (bank), Q1 FY27:** GNPA, slippages, upgrades and recoveries, write-offs, credit cost, CASA and the profit bridge are all published. Universal slots fire here too: reported profit before tax rose about 18% while pre-provision profit fell about 21% because provisions dropped about 79% (U2), and bad-loan rupees rose on the quarter even though the ratio improved (U1). The prior-year base probably includes a one-off, which is exactly the confounder the gates demand adjusting.
- **HDFC Life (life insurer), Q1 FY27:** APE, VNB, VNB margin, persistency, solvency, embedded value and channel mix are published. Universal slots fire: 13-month persistency fell to 84% from 86% while growth continued (U1), solvency of 185% against 192% a year earlier despite a ₹1,000 crore capital infusion from HDFC Bank (U3), and moderate growth in the parent-bank channel (U9).

### 4.4 Scoring on eight Bajaj Finance leads (pipeline scenario: calculations run in code)

| Lead | Score | Outcome | Gates | Evidence label |
|---|---|---|---|---|
| L1 stress flat in rupees, ratio flattered | **94.0** | Strong candidate | pass | Moderate |
| L2 MSME and captive 2W concentration | **79.2** | Moderate | pass | Moderate |
| L3 margin flat while funding got cheaper | 72.8 | Moderate | fail C, E | Weak |
| L4 deposit share shrinking | 68.0 | Moderate | fail C | Weak |
| L6 capital cushion thinned | 59.0 (capped from 66.0) | Weak | fail C, D | Weak |
| L5 repeated provision overlays | 52.0 | Weak | fail C, D, E | Weak |
| L7 recoveries presentation change | 42.0 | No strong finding | fail A, C, D | Weak |
| L8 quarter-end vs average LCR | 41.6 | No strong finding | fail C, D, E | Weak |

- **Result:** L1 clear leader (14.8 points ahead of L2). This agrees with my earlier manual verdicts.
- **When evidence is entered exactly as gathered by hand** (no Tier 1 document opened, no code run), **no lead passes the gates**. That is correct and shows the gate is strict, not decorative.
- **Gate C ablation:** without the counterargument-categories gate, L4 would wrongly reach gate-passing status. The gate matters.
- **Limitation:** these checklist answers are my own judgement from our conversation. They test the logic of the system, not the accuracy of an unattended AI rater.

### 4.5 Reproducibility
- **Weight sensitivity:** every weight randomly changed by up to 30% and renormalised: same top lead in **100%** of 4,000 trials.
- **Rater noise** (each judged answer flipped with probability p; 4,000 trials per row; top lead same / top-2 order same):

| Scheme | p = 5% | p = 10% | p = 20% |
|---|---|---|---|
| Old: everything judged by one rater | 85.5% / 73.0% | 69.0% / 49.9% | 46.6% / 21.4% |
| Machine-checked fixed + single rater | 89.8% / 81.4% | 80.1% / 65.1% | 62.7% / 40.1% |
| Machine-checked fixed + double-score AND | 90.3% / 81.5% | 79.7% / 63.7% | 60.4% / 36.1% |
| **Machine-checked fixed + majority of 3 (adopted)** | **98.7% / 97.1%** | **94.5% / 89.3%** | 79.5% / 63.5% |

- **Reading:** if your AI rater disagrees with itself on about 10% of judged tests, majority-of-3 keeps the top lead stable about 94.5% of the time. At 20% noise it drops to about 80%, so measure your rater's real noise (the agreement rate) before trusting rankings.
- **Weakness of the sensitivity test:** it is easy to pass here because L1 beats L2 on almost every dimension. Re-run it on close pairs of leads from real runs.
- **Assumption:** noise is modelled as random flips. Real AI errors can be correlated, which would be worse. Test with real repeated runs.

---

## 5. What remains untested, and what to do next

1. **No live agent run** on any company. First priority: run the full pipeline on Bajaj Finance, HDFC Bank and HDFC Life; check that the lead lists look sensible and that the agent never states unsourced figures.
2. **Archetype slot points are my judgement.** Replace them with measured values: for each archetype, count how many slots a real run can fill from public documents.
3. **Rater noise is simulated.** Measure real agreement across three runs of the judged tests and recompute Section 4.5.
4. **Insurer, exchange and asset-manager modules** exist as slot definitions only. Write their formulas before the finals if time allows; otherwise the viability gate marks them LIMITED, which is an honest fallback.
5. **Index membership changes.** Read the NIFTY 50 list at run time.
6. **Thresholds** (59/79 caps, bands, 12-of-18 gate, 80% agreement) are heuristics. They are set once for the whole track, never per company, which keeps you within the no-company-specific-tuning rule.

## 6. How to re-run the tests
```
cd scoring_code
python3 run_tests.py      # scoring, gates, discrimination, sensitivity, archetype matrix
python3 noise_test.py     # rater-noise comparison of schemes
```
