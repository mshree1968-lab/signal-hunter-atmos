# Round 1 submission — one-page draft (Track A)

Replace `[...]` placeholders. Target 550–650 words so it prints on one page at 10.5pt.
Save as `[TeamName]_TrackA_Round1.pdf` (brief p.103). Deadline: 19 Oct 2026, 23:59 IST.

---

**Team:** [Team name] · **Track:** A — Banking, NBFCs & Financial Services

### 1. Idea
We are not building a summariser. We are building **Signal Hunter**, an investigator that treats a
company as a set of claims to be tested. It reads filings and management commentary together, converts
every mismatch between them into a numbered *lead*, ranks the leads with a fixed rubric, and then tries
to destroy the best one. The output is one finding that survives its own counterargument, with a full
evidence chain and a dated condition that would prove it wrong.

The reason this finds non-obvious things: the signal is almost never a hidden document. It is a gap
between two public facts — a ratio improving while the rupee amount worsens, a KPI redefined the quarter
after it deteriorated, a rating rationale naming a lender the company never mentions.

### 2. Stack
[LLM(s)] for extraction and judging · [agent framework] · PDF text + table extraction with OCR fallback ·
a provenance store (SQLite/JSON) · **Python for every calculation** · `scoring.py` for gates and scores.
The AI never does arithmetic and never assigns a score; it only answers pass/fail with evidence ids.

### 3. Workflow
Entity resolution and archetype classification → collect by source family (filings, exchange, rating
agencies, RBI/industry, peers) → extract facts, claims, events and definitions with provenance → compute
metrics in code → evaluate 17 relationships → each flagged edge becomes a lead → rank → investigate the
top lead → build the strongest counterargument → write a falsification condition → verify every claim
against its saved excerpt → report. A 30-minute full run and a 10-minute express run use the same steps.

### 4. Track A, and why it generalises
The system reads the NIFTY 50 list at run time and classifies each company into an **archetype**
(bank, retail NBFC, housing finance, life insurer, general insurer, asset manager, exchange, holding
company). Nine universal slots — growth vs quality, profit quality, capital, funding, claims vs delivery,
definition changes, governance, peer benchmark, concentration — are filled with that archetype's
formulas, which are fixed in the prompt and never invented at run time. Cases with thin disclosure fall
to a stated LIMITED mode instead of being refused or guessed.

**Coverage of the 12 Track A NIFTY 50 names today:** 7 on the lender module (Axis, HDFC Bank, ICICI,
Kotak, SBI, Bajaj Finance, Shriram); 4 on archetype modules (HDFC Life, SBI Life, Bajaj Finserv,
BSE Ltd); 1 disclosed as LIMITED (Jio Financial, under five years of listed history). Unlisted entities
are out of scope and are handled by an explicit rule, not by improvisation.

### 5. Triangulation and contradiction detection
Every lead must be confirmed by a source from a **different family** than the one that produced it
(a presentation flag needs a rating rationale, a peer or RBI data). Five patterns generate leads: claim
vs number, number vs number, year vs year (definitions and disclosures), company vs peers, company vs an
independent source. Sources carry reliability tiers; a flag that cannot be confirmed outside its own
family fails Gate A and stays in the Lead Register rather than becoming the discovery.

### 6. Self-falsification
For the top lead the agent searches six categories of counter-evidence: management's own explanation,
accounting/regulatory change, peer and sector norms, one-off events, independent views, and news that
contradicts. The strongest surviving alternative is reported with a rating. The falsification condition
names a measurable item, a threshold taken from the company's own history, peers or guidance, and a real
checkpoint — and it must be able to fail in both directions. Ratios are always paired with rupee amounts
and a write-off-adjusted view, so a finding cannot survive on a denominator effect.

### 7. Output
A report with the brief's eight elements (discovery, why it matters, evidence, timeline, numbers,
counterargument, falsification condition, evidence strength), plus the Lead Register, relationship map,
calculation log, source list and verification log — mirrored as JSON so every claim links to its source.
A dashboard can be rendered from the same JSON.

### 8. Build plan
19–23 Oct: provenance store, calculation module for the core metrics, collectors for presentations,
results, one rating report and annual-report notes; regression runs on Bajaj Finance and one bank.
23–25 Oct: insurer/exchange modules, peer module, verification pass, demo path; final run on a company
we did not design around. Demo shows the Lead Register within 8 minutes, with the full report completing
after it.
