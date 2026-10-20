import random, copy
from scoring import *
from scoring import MACHINE, JUDGED
import run_tests as rt   # re-uses the lead data (prints are fine)

def rate(truth, p, scheme, rnd):
    """One judged answer under a rating scheme; each rater flips with prob p."""
    r = lambda: (not truth) if rnd.random() < p else truth
    if scheme == "single": return r()
    if scheme == "double_and": return r() and r()                 # conservative: both raters must pass
    if scheme == "majority3":  return (r() + r() + r()) >= 2
    raise ValueError

def run(p, scheme, machine_fixed, trials=4000, seed=5):
    rnd = random.Random(seed)
    base_rows,_ = score_all(rt.leads, DIMS_V4)
    base_top = [r["id"] for r in base_rows if r["gates_passed"]]
    same1 = same2 = none = 0
    for _ in range(trials):
        ls = copy.deepcopy(rt.leads)
        for l in ls:
            for d in DIMS_V4:
                new = []
                for i, v in enumerate(l.tests[d]):
                    if machine_fixed and i in MACHINE[d]: new.append(v)
                    else: new.append(rate(v, p, scheme, rnd))
                l.tests[d] = new
            # judged gates E and H are also rater answers
            l.confounders_checked = rate(l.confounders_checked, p, scheme, rnd)
            l.is_company_headline = rate(l.is_company_headline, p, scheme, rnd)
            if not machine_fixed:   # old behaviour: counts jittered as if judged
                j = lambda x: x-1 if rnd.random()<p/2 else x+1 if rnd.random()<p else x
                l.independent_families = max(0,j(l.independent_families))
                l.counter_categories_searched = max(0,j(l.counter_categories_searched))
                l.falsification_criteria_met = min(5,max(0,j(l.falsification_criteria_met)))
        rows,_ = score_all(ls, DIMS_V4)
        top = [r["id"] for r in rows if r["gates_passed"]]
        same1 += top[:1] == base_top[:1]; same2 += top[:2] == base_top[:2]; none += (not top)
    return same1/trials*100, same2/trials*100, none/trials*100

print("\n== Rater-noise test: scheme comparison (4,000 trials each)")
print(f"{'scheme':<44}{'p':>5}  top-1 same  top-2 order  no-lead-passes")
cfg = [("single rater, everything judged (old)", "single", False),
       ("machine-checked fixed + single rater", "single", True),
       ("machine-checked fixed + double-score AND", "double_and", True),
       ("machine-checked fixed + majority of 3", "majority3", True)]
for name, sch, mf in cfg:
    for p in (0.05, 0.10, 0.20):
        a,b,c = run(p, sch, mf)
        print(f"{name:<44}{p:>5.2f}  {a:8.1f}%  {b:10.1f}%  {c:12.1f}%")
print("\nMachine-checked tests:", sum(len(v) for v in MACHINE.values()), "of 30;  judged:", sum(len(v) for v in JUDGED.values()))
