import random, statistics, copy
from scoring import *

T, F = True, False
def mk(id, name, disc, evid, cross, temp, fals, rob, expl, gen, **kw):
    return Lead(id, name, {"discovery": disc, "evidence": evid, "cross_source": cross,
        "temporal": temp, "falsifiability": fals, "robustness": rob,
        "explainability": expl, "generality": gen}, **kw)

# Evidence status is "as actually gathered in our conversation": no Tier-1 audited note was opened
# and arithmetic was not run in a code tool, so tests evidence[0] and evidence[1] are False for all leads.
leads = [
 mk("L1","Stress flat in rupees; GNPA ratio flattered by growth and write-offs",
    [T,T,T,T,T],[F,F,T,T,T],[T,T,T,T,T],[T,F,T,T,T],[T,T,T,T,T],[T,T,T,T,T],[T]*5,[T]*5,
    independent_families=4,has_tier1_or_2=T,counter_categories_searched=6,falsification_criteria_met=5,
    confounders_checked=T,claims_verified=T,source_documents=6,counter_strength="Moderate"),
 mk("L2","MSME + captive 2W: ~10% of AUM, ~38% of bad loans",
    [T,F,T,T,F],[F,F,T,T,T],[T,T,T,F,T],[F,T,T,T,T],[T,T,T,T,T],[T,T,T,T,F],[T]*5,[T]*5,
    independent_families=4,has_tier1_or_2=T,counter_categories_searched=5,falsification_criteria_met=5,
    confounders_checked=T,claims_verified=T,source_documents=6,counter_strength="Moderate"),
 mk("L3","Cost of funds fell but margin flat while peers' widened",
    [T,T,T,T,F],[F,F,T,T,T],[T,T,T,T,F],[T,T,T,T,F],[T,T,T,T,F],[F,T,F,F,T],[T]*5,[T]*5,
    independent_families=3,has_tier1_or_2=T,counter_categories_searched=3,falsification_criteria_met=4,
    confounders_checked=F,claims_verified=T,source_documents=4,counter_strength="Moderate"),
 mk("L4","Deposit share shrinking while loans grow",
    [T,T,T,T,F],[F,F,T,T,T],[T,T,F,F,F],[T,T,T,T,F],[T,T,T,T,F],[F,F,F,T,T],[T]*5,[T,T,T,F,T],
    independent_families=3,has_tier1_or_2=T,counter_categories_searched=2,falsification_criteria_met=4,
    confounders_checked=T,claims_verified=T,source_documents=3,counter_strength="Weak"),
 mk("L5","Repeated provision overlays (Rs 1,844 cr over 3 quarters)",
    [T,T,T,T,T],[F,F,T,T,T],[T,F,F,F,F],[F,F,F,F,T],[T,T,F,F,F],[F,T,F,F,F],[T]*5,[T,T,T,F,T],
    independent_families=2,has_tier1_or_2=T,counter_categories_searched=3,falsification_criteria_met=2,
    confounders_checked=F,claims_verified=T,source_documents=3,counter_strength="Weak"),
 mk("L6","Capital cushion thinned as growth outran capital",
    [F,F,T,T,T],[F,F,T,T,T],[T,T,F,F,F],[T,T,T,T,T],[T,T,T,F,F],[F,T,F,T,T],[T]*5,[T,T,T,F,T],
    independent_families=2,has_tier1_or_2=T,counter_categories_searched=3,falsification_criteria_met=3,
    confounders_checked=T,claims_verified=T,source_documents=3,unresolved_strong_counter=T,counter_strength="Strong"),
 mk("L7","Recoveries moved into loan losses (presentation change)",
    [F,T,T,T,F],[F,F,T,T,T],[T,F,F,F,F],[F,T,F,F,T],[F,F,F,F,F],[F,T,F,T,F],[T]*5,[T,T,T,F,T],
    independent_families=1,has_tier1_or_2=T,counter_categories_searched=2,falsification_criteria_met=0,
    confounders_checked=T,claims_verified=T,source_documents=3,counter_strength="Weak"),
 mk("L8","Quarter-end LCR 115% vs reported daily average 231%/158%",
    [T,T,T,F,T],[F,F,T,F,F],[T,F,F,F,F],[F,F,F,F,F],[T,T,T,F,F],[F,T,F,F,F],[T,T,T,F,T],[T,T,T,F,T],
    independent_families=2,has_tier1_or_2=T,counter_categories_searched=1,falsification_criteria_met=3,
    confounders_checked=F,claims_verified=T,source_documents=2,unresolved_conflict=T,counter_strength="Weak"),
]
for l in leads: validate(l, strict=False)
import copy as _c
leads_asgathered = _c.deepcopy(leads)
for l in leads:                      # scenario B: P3 executed in code -> derived numbers reproduced
    l.tests["evidence"][1] = True


def show(title, rows, verdict):
    print(f"\n== {title}  ->  {verdict}")
    for r in rows:
        g = "PASS" if r["gates_passed"] else "fail:" + ",".join(x.split('_')[0] for x in r["failed"])
        print(f"{r['id']}  raw {r['raw']:5.1f}  final {r['final']:5.1f}  {r['outcome']:<18} ev:{r['evidence_label']:<8} gates {g}  {'; '.join(r['caps'])}")

ra, va = score_all(leads_asgathered, DIMS_V4); show("v4, evidence AS GATHERED in chat (no code run)", ra, va)
r3, v3 = score_all(leads, DIMS_V3); show("v3 (8 dimensions), pipeline scenario", r3, v3)
r4, v4 = score_all(leads, DIMS_V4); show("v4 (6 dimensions + run QC), pipeline scenario", r4, v4)

# 1) Discrimination test: which dimensions give identical results across leads?
print("\n-- Discrimination (points per lead, by dimension, v3 weights)")
for d,w in DIMS_V3.items():
    pts=[sum(l.tests[d])/5*w for l in leads]
    print(f"{d:<15} weight {w:>2}  min {min(pts):4.1f} max {max(pts):4.1f}  spread {max(pts)-min(pts):4.1f}")

# 2) Rater-noise Monte Carlo: flip each checklist answer with prob p
def mc(dims, p, trials=4000, seed=7):
    rnd = random.Random(seed); top_same=0; top3_same=0; gate_flip=0
    base_rows,_ = score_all(leads, dims)
    base_top = [r["id"] for r in base_rows if r["gates_passed"]]
    for _ in range(trials):
        ls = copy.deepcopy(leads)
        for l in ls:
            for d in dims:
                l.tests[d] = [(not v) if rnd.random() < p else v for v in l.tests[d]]
            def jit(x):
                r = rnd.random()
                return x-1 if r < p/2 else x+1 if r < p else x
            l.independent_families = max(0, jit(l.independent_families))
            l.counter_categories_searched = max(0, jit(l.counter_categories_searched))
            l.falsification_criteria_met = min(5, max(0, jit(l.falsification_criteria_met)))
        rows,_ = score_all(ls, dims)
        top = [r["id"] for r in rows if r["gates_passed"]]
        if top[:1] == base_top[:1]: top_same += 1
        if top[:2] == base_top[:2]: top3_same += 1
        if not top: gate_flip += 1
    return top_same/trials, top3_same/trials, gate_flip/trials
print("\n-- Rater-noise test (4,000 trials; each checklist answer flipped with prob p)")
for p in (0.05,0.10,0.20):
    a,b,c = mc(DIMS_V4,p); print(f"p={p:.2f}: same top lead {a*100:5.1f}%   same top-2 order {b*100:5.1f}%   runs with no lead passing gates {c*100:4.1f}%")

# 3) Weight-sensitivity: random +/-30% weights, renormalised to 100
def sens(trials=4000, seed=11):
    rnd = random.Random(seed); same=0
    base=[r["id"] for r in score_all(leads, DIMS_V4)[0] if r["gates_passed"]][0]
    for _ in range(trials):
        w = {d: v*rnd.uniform(0.7,1.3) for d,v in DIMS_V4.items()}; s=sum(w.values())
        w = {d: v*100/s for d,v in w.items()}
        top=[r["id"] for r in score_all(leads, w)[0] if r["gates_passed"]][0]
        same += (top==base)
    return same/trials
print(f"\n-- Weight sensitivity (+/-30% on every weight): same top lead in {sens()*100:.1f}% of 4,000 trials")

# 4) Gate-strictness check: what if gate C (4 counter categories) were dropped?
import scoring
orig = scoring.gates
def no_c(l):
    g = orig(l); g["C_four_counter_categories"]=True; return g
scoring.gates = no_c
rows,verdict = score_all(leads, DIMS_V4)
print("\n-- Without gate C, gate-passing leads:", [(r['id'], r['final']) for r in rows if r['gates_passed']])
scoring.gates = orig

# 5) Archetype coverage / viability test (Track A universe)
SLOTS = ["U1 growth-vs-quality","U2 profit quality","U3 capital/solvency","U4 funding/liquidity/float",
         "U5 claims-vs-delivery","U6 definition/policy changes","U7 governance/ownership","U8 peers+independent source","U9 concentration"]
ARCH = {  # 2 = standard public Tier1-2 data, 1 = partial / needs adaptation, 0 = not applicable or not available
 "Private bank (HDFC, ICICI, Axis, Kotak)":      [2,2,2,2,2,2,2,2,2],
 "PSU bank (SBI; BoB, PNB, Canara...)":          [2,2,2,2,1,1,1,2,2],
 "NBFC retail lender (Bajaj Fin, Shriram, Chola, Muthoot)":[2,2,2,2,2,2,2,2,2],
 "Newly demerged / early-stage lender (Jio Financial)":    [1,1,2,1,1,1,2,1,1],
 "Holding company (Bajaj Finserv)":              [2,2,1,1,1,1,2,2,2],
 "Life insurer (HDFC Life, SBI Life)":           [2,2,2,1,2,2,2,2,2],
 "General insurer (ICICI Lombard)":              [2,2,2,1,1,2,2,2,2],
 "Exchange / market infrastructure (BSE)":       [1,2,1,0,2,2,2,1,1],
 "Asset manager (HDFC AMC)":                     [1,2,1,0,2,2,2,2,2],
 "Government lender (PFC, REC, IRFC)":           [2,2,2,2,1,2,1,2,2],
 "Card / specialty lender (SBI Cards)":          [2,2,2,2,2,2,2,2,2],
 "Small finance bank / housing finance co.":     [2,2,2,2,1,1,2,1,2],
}
print("\n-- Applicability / viability (18 = every universal slot fully testable)")
for a,s in ARCH.items():
    tot=sum(s); must = s[0]>=1 and s[1]>=1 and s[7]>=1
    mode = "FULL" if tot>=12 and must else "LIMITED"
    zeros=[SLOTS[i].split()[0] for i,v in enumerate(s) if v==0]
    print(f"{a:<58} {tot:>2}/18  {mode:<8} n/a: {','.join(zeros) or '-'}")
