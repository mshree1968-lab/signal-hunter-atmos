"""Builds the Round 1 report (Word). Numbers are taken from the real run outputs in outputs/*.json."""
import json, sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

ROOT = Path(__file__).resolve().parent.parent
TEAM = sys.argv[1] if len(sys.argv) > 1 else "Madhushree C S (solo)"
OUTFILE = ROOT / "submission" / "TeamName_TrackA_Round1.docx"


def run_facts(name):
    j = json.loads((ROOT / "outputs" / f"Signal_Hunter_Report_{name}.json").read_text(encoding="utf-8"))
    facts = j["facts"]
    return dict(facts=len(facts), verified=sum(bool(f.get("verified")) for f in facts),
                docs=len(j["documents"]), calcs=len(j["calcs"]),
                rel=j["relationships"].get("summary", {}), verdict=j["scores"].get("verdict", ""),
                leads=len(j["scores"].get("rows", [])), cost=j["run"]["cost"]["estimated_usd"],
                edges={e["id"]: e["detail"] for e in j["relationships"].get("edges", []) if e["status"] == "FLAGGED"})


B, A = run_facts("Bajaj_Finance"), run_facts("Axis_Bank")

doc = Document()
sec = doc.sections[0]
sec.page_height, sec.page_width = Cm(29.7), Cm(21.0)
sec.left_margin = sec.right_margin = Cm(1.6)
sec.top_margin = sec.bottom_margin = Cm(1.3)
st = doc.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(9.5)
st.paragraph_format.space_after = Pt(2)
st.paragraph_format.line_spacing = 1.0
NAVY = RGBColor(0x1F, 0x3A, 0x5F)


def h(text):
    p = doc.add_paragraph()
    p.paragraph_format.space_before, p.paragraph_format.space_after = Pt(5), Pt(1)
    r = p.add_run(text); r.bold = True; r.font.size = Pt(10.5); r.font.color.rgb = NAVY


def para(*parts):
    """parts: strings; a string starting with '**' is bold."""
    p = doc.add_paragraph()
    for s in parts:
        if s.startswith("**"):
            p.add_run(s[2:]).bold = True
        else:
            p.add_run(s)
    return p


def bullet(*parts):
    p = para(*parts)
    p.style = doc.styles["List Bullet"]
    p.paragraph_format.space_after = Pt(0)
    return p


def shade(cell, hex_fill):
    tcPr = cell._tc.get_or_add_tcPr()
    s = OxmlElement("w:shd"); s.set(qn("w:val"), "clear"); s.set(qn("w:color"), "auto"); s.set(qn("w:fill"), hex_fill)
    tcPr.append(s)


def table(header, rows, widths):
    t = doc.add_table(rows=1, cols=len(header))
    t.style = "Table Grid"
    for i, txt in enumerate(header):
        c = t.rows[0].cells[i]; c.text = ""; r = c.paragraphs[0].add_run(txt); r.bold = True; r.font.size = Pt(8.5)
        shade(c, "DCE6F1")
    for row in rows:
        cells = t.add_row().cells
        for i, txt in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(txt).font.size = Pt(8.5)
    for row in t.rows:
        for i, w in enumerate(widths):
            row.cells[i].width = Cm(w)
            row.cells[i].paragraphs[0].paragraph_format.space_after = Pt(0)
    return t


# ---------------------------------------------------------------- title
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run("Signal Hunter: an AI investigator that tests company stories instead of summarising them")
r.bold = True; r.font.size = Pt(13); r.font.color.rgb = NAVY
p = doc.add_paragraph(); p.alignment = WD_ALIGN_PARAGRAPH.CENTER
p.add_run(f"ATMOS 2026 \"Finding the Next Signal\"  |  Track A: Banking, NBFCs and Financial Services  |  "
          f"Round 1  |  {TEAM}  |  20 October 2026").font.size = Pt(9)

# ---------------------------------------------------------------- 1 idea
h("1. The idea")
para("Anyone can summarise a results deck. Signal Hunter does something else: it treats every public number as a "
     "claim to be checked. It reads the company's own documents, finds places where two public facts do not fit "
     "together (for example, a bad-loan ratio that improves while bad loans in rupees go up), turns each mismatch "
     "into a numbered ", "**lead", ", and then tries to prove its best lead wrong. It reports one finding only if "
     "the finding survives. Otherwise it says ", "**\"No Strong Finding\"", " and shows what it checked. "
     "The key rule: ", "**the AI never does arithmetic and never picks the winner; Python code does.")

# ---------------------------------------------------------------- 2 workflow + stack
h("2. How it works (one company name in, one report out)")
steps = [("Find documents", "searches the web, scores every result by fixed rules (official site, PDF, right document "
          "type, right quarter, not a group company), downloads it, opens it and rejects it if the company or quarter is not inside."),
         ("Read", "Claude finds the right pages (asset quality, segment tables) and reads at most 4 pages at a time."),
         ("Save facts with proof", "every number is stored with document, page and an exact excerpt. Code re-opens the page "
          "and checks the words and the number are really there; failed facts are not used."),
         ("Calculate in code", "fixed formulas: growth, Stage 3 %, write-off-adjusted GNPA, shares, insurer/exchange/AMC formulas."),
         ("Relate", "code tests 17 relationships (R1-R17), e.g. loan growth vs bad-loan growth, Stage 2 vs Stage 3, "
          "PPOP vs PBT growth, segment share of bad loans vs share of loans: CLEAN, FLAGGED or NOT-TESTABLE."),
         ("Score", "flagged edges become leads. 8 hard gates, then 30 yes/no tests; 18 tests are filled by code from the "
          "logs, so the AI cannot award itself points."),
         ("Report", "Word + JSON with the brief's eight elements, Lead Register, relationship map, evidence trail, "
          "calculation log, source list, verification log and run cost.")]
for i, (a, b) in enumerate(steps, 1):
    p = para(f"**{i}. {a}: ", b); p.paragraph_format.left_indent = Cm(0.3); p.paragraph_format.space_after = Pt(0)
para("**Stack: ", "Python 3; Anthropic Claude Sonnet 5.5 with tool use (reading, judging, writing) and Claude web search; "
     "free DuckDuckGo search first to keep cost low; pypdf; python-docx; pytest. Public, free sources only. "
     "Express run: about 1 minute and US$ 0.15-0.35; hard caps of 25 tool calls and US$ 1.50 per run.")

# ---------------------------------------------------------------- 3 generality / triangulation / time / falsification
h("3. Why it works for any Track A company")
para("No company names, peers or thresholds are written into the finder or the scoring. The agent first classifies "
     "the company into an archetype (bank, NBFC, housing finance, life insurer, general insurer, AMC, exchange, holding "
     "company) and uses that archetype's fixed formulas and document list. Companies with thin disclosure (for example "
     "a newly listed one) run in a stated LIMITED mode instead of being refused or guessed.")
h("4. Triangulation, time and self-falsification")
bullet("**Triangulation: ", "documents are grouped into families by code: A company, B exchange/regulator, C rating "
       "agency. A lead can only become the discovery if two independent families support it (Gate A). News and "
       "broker pages are kept as leads only, never as evidence.")
bullet("**Contradictions: ", "five patterns: claim vs number, number vs number, year vs year (redefined metrics), "
       "company vs peers, company vs an independent source.")
bullet("**Time: ", "every comparison uses the same quarter one year earlier and rupee amounts, not only ratios, so a "
       "ratio cannot look better just because the loan book grew (denominator rule).")
bullet("**Proving itself wrong: ", "for the top lead it must search six kinds of counter-evidence (management's "
       "explanation, accounting change, sector trend, one-off event, rating agency view, contradicting news) and write "
       "a falsification test: \"if [item] does [change] by [dated checkpoint], the finding is not supported\", with a "
       "threshold from the company's own history.")

# ---------------------------------------------------------------- 5 real results
h("5. Real test results (run on 20 October 2026, no human help during the runs)")
r1 = B["edges"].get("R11", "").split("; ")
msme = next((x for x in r1 if x.startswith("msme")), "")
cap = next((x for x in r1 if x.startswith("captive")), "")
table(["Test", "What happened", "Result"], [
    ["Automated code tests", "11 pytest tests (formulas, peers, scoring fixes, R1-R17, page check, report) + 15 finder checks",
     "all pass"],
    ["Ranking stability", "noise_test.py on the 8 leads of our earlier hand-run Bajaj study: each judged answer flipped at random 10% of the time, 4,000 trials",
     "same top lead 94.5%"],
    ["Bajaj Finance (live)", f"found and verified its Q1 FY27 investor presentation by search; {B['facts']} facts, "
     f"{B['verified']} confirmed on the page by code; {B['calcs']} calculations; flagged R11: MSME {msme.split(': ',1)[-1]}; "
     f"captive 2W {cap.split(': ',1)[-1]}; flagged R2 (Stage 2 down Rs 756 cr, Stage 3 up Rs 723 cr)",
     f"No Strong Finding ({B['leads']} leads, all fail Gate A: one source family). Cost US$ {B['cost']:.2f}"],
    ["Axis Bank (live, never designed around)", f"found Q2 FY27 results filed on NSE (17 Oct 2026); {A['facts']} facts, "
     f"{A['verified']} confirmed; flagged R5: {A['edges'].get('R5', '')}",
     f"No Strong Finding (one document). Cost US$ {A['cost']:.2f}"],
    ["Honest failure caught", "first Bajaj run downloaded Bajaj Housing Finance files; fixed with a full-name and "
     "group-company check, now covered by a test", "fixed"],
], [3.2, 10.6, 4.0])
para("Both live runs ended in \"No Strong Finding\". This is the system working as designed: the leads are real and "
     "checkable, but each rests on one source family, so the gates refuse to call them a discovery.").paragraph_format.space_before = Pt(2)

# ---------------------------------------------------------------- 6 proven vs not
h("6. What is proven, and what is not yet tested")
table(["Proven today (shown above)", "Not yet tested or built"], [
    ["Unattended document finding for an NBFC and a bank; group-company files rejected",
     "Insurer, exchange, AMC and holding-company runs (formulas exist and are unit-tested only)"],
    ["Every saved number re-checked on its page by code; numbers that fail (2 in the Axis run) are left out automatically",
     "Automatic peers and RBI sector data (so R14 and cross-source peer tests stay false)"],
    ["All arithmetic, relationships, gates and scores in tested code", "Three independent AI rating passes with majority vote (one pass today)"],
    ["Honest \"No Strong Finding\" when evidence is thin", "Using rating-agency web pages (found, but old and not used yet); OCR for scanned PDFs"],
    ["Low cost and speed: ~1 minute, under US$ 0.40 per express run", "Five-year history; a full 30-minute run; results are not identical run to run"],
], [8.9, 8.9])

# ---------------------------------------------------------------- 7 criteria map
h("7. How this answers the judging criteria")
table(["Criterion", "Where it is shown"], [
    ["Clarity and feasibility", "Sections 1-2; working code and two real runs (Section 5)"],
    ["Originality / novelty", "Tests claims against numbers instead of summarising; findings need two documents and a calculation"],
    ["Discovery quality", "Leads come from flagged relationships, e.g. MSME share of bad loans vs share of loans (Bajaj)"],
    ["Evidence quality and explainability", "Every number has document, page, excerpt and a code check; every figure has a fact or calculation id"],
    ["Cross-source reasoning (triangulation)", "Gate A needs two independent source families (Section 4)"],
    ["Temporal reasoning", "Same-quarter-last-year comparisons in rupees and ratios; dated falsification checkpoints"],
    ["Falsifiability and robustness", "Six counter-evidence categories, falsification test, hard gates, 94.5% ranking stability"],
    ["Generality and autonomy", "Archetypes, no company names in finder or scoring; unseen Axis Bank ran unattended"],
], [5.0, 12.8])

# ---------------------------------------------------------------- 8 plan
h("8. Plan to the finals (21-25 October)")
para("21-22 Oct: add the rating rationale and annual-report notes as a second family, and two automatic peers. "
     "23 Oct: three-pass judging with agreement rate; one insurer and one exchange run. 24 Oct: cached documents for an "
     "offline demo; rehearse. 25 Oct: live express run on a company the judges choose.")

OUTFILE.parent.mkdir(exist_ok=True)
doc.save(OUTFILE)
print(OUTFILE)
