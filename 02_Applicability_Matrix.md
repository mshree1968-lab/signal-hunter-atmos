# Track A Applicability Matrix (as of 19 October 2026)

Purpose: put this in the Round-1 PDF as one table, and keep it as the agent's coverage contract.
It is the single strongest answer to the brief's "does the same system work for every company in your
track" criterion (brief p.118, p.120). Verify membership at run time (index lists change) — do not
hard-code this table into the agent.

## 1. The NIFTY 50 Track A universe — 12 names

| # | Company | Archetype | Peer scale metric | Module | Mode | Primary Tier 1/2 sources | Known gap (stated, not hidden) |
|---|---|---|---|---|---|---|---|
| 1 | Axis Bank | Private bank | Advances | §9 `[Bank]` | FULL | Pillar 3, quarterly results, AR notes, rating rationale | Co-lending/off-book relationship R8 is thin |
| 2 | HDFC Bank | Private bank | Advances | §9 `[Bank]` | FULL | as above | Post-merger ratios need restated comparatives |
| 3 | ICICI Bank | Private bank | Advances | §9 `[Bank]` | FULL | as above | Group entities need look-through |
| 4 | Kotak Mahindra Bank | Private bank | Advances | §9 `[Bank]` | FULL | as above | Consolidated mix includes insurance/broking |
| 5 | State Bank of India | PSU bank | Advances | §9 `[Bank]` | FULL | AR segment notes, Pillar 3, RBI | Size band fails: peers are 5–10x smaller → compare trends, not levels |
| 6 | Bajaj Finance | Retail NBFC | AUM | §9 full | FULL | Stage/ECL note, presentations, rating rationales | Best-covered name — use as the regression test |
| 7 | Shriram Finance | NBFC (vehicle/commercial) | AUM | §9 full | FULL | AR notes, rating rationales, ALM | Segment GNPA disclosed only annually |
| 8 | Jio Financial Services | Newly demerged financial holdco/NBFC | AUM / consolidated assets | LIMITED path | **LIMITED** | Consolidated results, parent filings for pre-2023 history | Under 5 years as a listed entity; structure changed post-demerger |
| 9 | Bajaj Finserv | Holding company | Consolidated assets | §8B holding | FULL (new) | Segment results by subsidiary, standalone statements | Lender ratios must not be applied to the parent total |
| 10 | HDFC Life | Life insurer | APE | §8B insurer | FULL (new) | IRDAI public disclosures, EV, quarterly, AR | Bancassurance dependence is a disclosure, not a ratio |
| 11 | SBI Life | Life insurer | APE | §8B insurer | FULL (new) | as above | Same |
| 12 | **BSE Ltd** | **Exchange** | **Revenue** | §8B exchange | FULL (new) | Quarterly results, SEBI data, MCX as peer | U4 not applicable; settlement-guarantee fund instead of funding mix |

**Result to state in the submission:** 7 of 12 names run on the fully specified lender module; 4 run on
the §8B modules added in patch P1; 1 (Jio Financial) runs LIMITED with that limitation disclosed.
**None are refused, and none are hand-tuned.**

> Note: BSE Ltd replaced Wipro in the NIFTY 50 effective 30 September 2026, so the pool is 12 names,
> not the 11 assumed in the v5 report. Treat the v5 §4.1 list as superseded.

## 2. Non-NIFTY listed companies (tie-break pool, brief p.110)

| Group | Examples | Module | Expected mode | Constraint |
|---|---|---|---|---|
| Private/PSU banks | BoB, PNB, Canara, Union, IDFC First, Federal, Yes | §9 `[Bank]` | FULL | Presentations thinner than the top 5; rely on AR + Pillar 3 |
| Retail/vehicle NBFCs | Chola, Muthoot, Tata Capital, Bajaj Housing, LIC Housing | §9 full | FULL | HFCs need the housing variant of Stage disclosures |
| Government lenders | PFC, REC, IRFC | §9 full | FULL | Concentrated single-sector exposure; rating rationales essential |
| Card/specialty lender | SBI Cards | §9 full | FULL | Securitisation and co-brand disclosure |
| General insurer | ICICI Lombard, New India (unlisted) | §8B general insurer | FULL | New India is unlisted → §15A applies |
| Asset managers | HDFC AMC, Nippon, UTI | §8B AMC | FULL (no U4) | Scheme-level concentration needed for U9 |
| Exchanges | MCX, CDSL (depository) | §8B exchange | FULL (no U4) | CDSL is a depository — adapt, no trading yield |

## 3. Unlisted / private companies (added by patch P3)

| Situation | Required behaviour |
|---|---|
| Unlisted subsidiary of a listed parent | Analyse the parent's consolidated filings; state the look-through basis |
| Unlisted with a DRHP | Use the DRHP for history, mark it Tier 1 for the period covered |
| Unlisted, no DRHP | MCA AOC-4 + charge records only → `LIMITED`; produce the eight elements only if 2+ families exist |
| Cannot resolve the name | Stop after two searches; do not guess a ticker |

## 4. Runtime mode rule (put this in code, not in prose)

```python
SCALE = {"bank": "advances", "nbfc": "aum", "hfc": "aum", "life": "ape",
         "general": "gwp", "amc": "aum", "exchange": "revenue", "holding": "cons_assets"}

def mode(slot_points):           # 9 slots, each 0/1/2
    total = sum(slot_points)
    must = slot_points[0] >= 1 and slot_points[1] >= 1 and slot_points[7] >= 1   # U1, U2, U8
    return ("FULL" if total >= 12 and must else "LIMITED"), total
```

Coverage grade to print in the report header: `FULL` = ≥12/18 and U1/U2/U8 ≥1; otherwise `LIMITED`.
