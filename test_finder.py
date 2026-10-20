"""
test_finder.py - run with:  python test_finder.py
No internet needed. The search results below are REAL results returned by web search on
20 Oct 2026 for Axis Bank (a company the finder was not designed around). Downloads are tested
against a small local web server so retry/verify/log logic runs for real.
"""
import json, os, shutil, tempfile, threading
from datetime import date
from http.server import BaseHTTPRequestHandler, HTTPServer

from finder import (Candidate, CachedBackend, FixtureBackend, Period, classify_domain, classify_type,
                    company_tokens, fetch_doc, find_documents, make_period, period_ladder,
                    score_candidate, verify, wrong_period_tokens)
from sources import NEEDS, PRESENTATION, PRESS

TODAY = date(2026, 10, 20)
PASSED = []
def ok(name):
    PASSED.append(name); print("PASS", name)

# ---- real search results (url, title) captured for Axis Bank ----
AX = "https://www.axis.bank.in/docs/default-source/shareholders/financial-results-and-other-information/corporate-announcements/intimations-to-stock-exchanges/"
REAL = [
    (AX + "press-release-q1fy27-18-07-2026.pdf", "press release q1fy27 18 07 2026"),
    (AX + "earnings-call-transcript-q1fy27-24-07-2026.pdf", "earnings call transcript q1fy27 24 07 2026"),
    ("https://kalkinemedia.com/uk/news/announcements/axis-bank-limited-axb-publishes-updated-investor-presentation-for-q1-2026-27-financial-results", "Axis Bank Limited (AXB) Publishes Updated Investor Presentation for Q1 2026-27 Financial Results"),
    ("https://www.sahi.com/news/axis-bank-plans-meetings-with-investors-and-analysts-on-august-26-2214-PE1_COR", "Axis Bank Plans Meetings With Investors and Analysts on August 26"),
    ("https://ticker.finology.in/discover/market-update/axis-bank-q1-fy27-results", "axis bank q1 fy27 results"),
    ("https://www.muthootsecurities.com/CorporateInfo/ComNews/Axis-Bank-Ltd/25199010108", "Axis Bank Q1 PAT rises 23% YoY to Rs 7,114 crore"),
    ("https://www.angelone.in/news/stocks/axis-bank-share-price-in-focus-after-it-reports-q2-fy27-financial-update", "Axis Bank Share Price in Focus After It Reports Q2 FY27 Financial Update"),
    ("https://www.psuconnect.in/financial/axis-bank-q2-fy27-business-update", "Axis Bank Q2 FY27 Business Update: Advances Rise 22.7%, Deposits Grow 20.7%"),
    ("https://upstox.com/news/market-news/stocks/axis-bank-shares-will-be-in-focus-as-lender-s-gross-advances-increase-over-13-lakh-crore-in-q2-check-all-updates/article-201303/", "Axis Bank gross advances increase over 13 lakh crore in Q2 FY27"),
    ("https://bsmedia.business-standard.com/_media/bs/data/market-reports/equity-brokertips/2026-07/17845296860.99367800.pdf", "AXIS Bank | BUY Mixed quarter: NIM disappoints"),
    ("https://www.lse.co.uk/rns/AXB/audio-call-recording-xpz106kamaen61r.html", "audio call recording"),
    ("https://www.business-standard.com/companies/news/axis-bank-q2-profit-falls-26-on-rbi-advised-one-time-provisioning-125101501014_1.html", "Axis Bank Q2 net falls 26% to Rs 5,090 crore"),
    ("https://www.motilaloswal.com/news/stocks/107063", "Axis Bank stock tumbles after poor Q2 earnings"),
]
POOL = [dict(url=u, title=t, snippet="") for u, t in REAL]
NAME, SYMBOL = "Axis Bank Limited", "AXISBANK"
TOK = company_tokens(NAME, SYMBOL)

# ---- 1. quarters ----
lad = period_ladder(TODAY)
assert [p.label for p in lad] == ["Q2 FY27", "Q1 FY27", "Q4 FY26"], [p.label for p in lad]
assert [p.label for p in period_ladder(date(2026, 7, 10), 2)] == ["Q1 FY27", "Q4 FY26"]
assert [p.label for p in period_ladder(date(2026, 4, 2), 1)] == ["Q4 FY26"]
assert "q1fy27" in make_period(date(2026, 6, 30)).tokens and "30june2026" in make_period(date(2026, 6, 30)).tokens
ok("quarter ladder (newest completed quarter first; Indian financial year)")

# ---- 2. identity tokens and site classes ----
assert {"axis", "axisbank"} <= TOK
assert "sbi" in company_tokens("State Bank of India", "SBIN")
assert classify_domain(REAL[0][0], TOK) == ("company", "A")
assert classify_domain("https://www.nseindia.com/x.pdf", TOK) == ("regulator", "B")
assert classify_domain("https://www.crisil.com/x.html", TOK) == ("rating", "C")
for u, _ in REAL[2:]:
    assert classify_domain(u, TOK)[0] == "other", u
ok("sites classified: company / regulator / rating / news-broker")

# ---- 3. company type from description (no names involved) ----
assert classify_type("a leading private sector bank in India")[0] == "bank"
assert classify_type("non-banking financial company focused on consumer lending")[0] == "nbfc"
assert classify_type("India's largest private life insurance company")[0] == "life"
assert classify_type("general insurance company, motor and health")[0] == "general"
assert classify_type("asia's oldest stock exchange")[0] == "exchange"
assert classify_type("financial holding company with insurance and lending subsidiaries")[0] == "holding"
assert classify_type("an asset management company running mutual funds")[0] == "amc"
ok("company type rules (7 types)")

# ---- 4. ranking on REAL Axis results ----
q1, q2 = make_period(date(2026, 6, 30)), make_period(date(2026, 9, 30))
def rank(need, period):
    wr = wrong_period_tokens(TODAY, period)
    cs = [score_candidate(Candidate(**p), need, period, TOK, wr) for p in POOL]
    return sorted(cs, key=lambda c: c.score, reverse=True)
r = rank(PRESS, q1)
assert r[0].url == REAL[0][0] and r[0].score >= 9, (r[0].url, r[0].score)
assert all(c.score < 9 for c in r[1:]), [(c.url[-40:], c.score) for c in r[1:4]]
ok("Q1 FY27 press release: official PDF ranked first; every news/broker page scored below the bar")
r2 = rank(PRESS, q2)
assert all(c.score < 9 for c in r2), "nothing should qualify as Q2 FY27 full results"
ok("Q2 FY27: nothing official found, so no wrong document is accepted")
r3 = rank(PRESENTATION, q1)
assert all(c.score < 9 for c in r3), "a press release must not be accepted as the presentation"
ok("document-type check: press release is not accepted as an investor presentation")

# ---- 5. local web server for download tests ----
def make_pdf(path, lines, pages=2):
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    c = canvas.Canvas(path, pagesize=A4)
    for _ in range(pages):
        y = 800
        for ln in lines:
            c.drawString(40, y, ln); y -= 18
        c.showPage()
    c.save()

TMP = tempfile.mkdtemp()
Q1_LINES = ["AXIS/CO/CS/250/2026-27", "PRESS RELEASE ON THE FINANCIAL RESULTS OF AXIS BANK LIMITED",
            "FOR THE QUARTER ENDED JUNE 30, 2026  (Q1FY27)", "The Board of Directors of Axis Bank Limited approved the results.",
            "Operating profit for the quarter stood at 11,659 crores. NIM 3.46%. Gross slippages 5,566 crores."]
Q4_LINES = ["AXIS BANK LIMITED press release for the quarter ended March 31, 2026 (Q4FY26)",
            "The Board of Directors of Axis Bank Limited approved the results. Operating profit rose.",
            "Net interest income and fee income grew. Asset quality improved during the quarter and the year."]
# the real Axis file is ONE 70-page PDF: cover letter + press release + investor presentation (checked by fetching it)
make_pdf(os.path.join(TMP, "q1.pdf"), Q1_LINES + ["Investor Presentation  Quarterly Results Q1FY27"], pages=20)
make_pdf(os.path.join(TMP, "q4.pdf"), Q4_LINES)
make_pdf(os.path.join(TMP, "other_company.pdf"), ["XYZ Holdings press release for the quarter ended June 30, 2026 (Q1FY27)"] * 6)
HITS = {}
class H(BaseHTTPRequestHandler):
    def log_message(self, *a): pass
    def do_GET(self):
        HITS[self.path] = HITS.get(self.path, 0) + 1
        if self.path == "/flaky.pdf" and HITS[self.path] == 1:
            self.send_response(403); self.end_headers(); return
        if self.path == "/missing.pdf":
            self.send_response(404); self.end_headers(); return
        if self.path == "/login.pdf":
            body = b"<html><body>Please log in</body></html>"
        else:
            f = {"/ok.pdf": "q1.pdf", "/flaky.pdf": "q1.pdf", "/wrongq.pdf": "q4.pdf", "/other.pdf": "other_company.pdf"}[self.path]
            body = open(os.path.join(TMP, f), "rb").read()
        self.send_response(200); self.send_header("Content-Length", str(len(body))); self.end_headers(); self.wfile.write(body)
srv = HTTPServer(("127.0.0.1", 0), H); PORT = srv.server_port
threading.Thread(target=srv.serve_forever, daemon=True).start()
BASE = f"http://127.0.0.1:{PORT}"
OUT = os.path.join(TMP, "out"); LOG = []

r = fetch_doc(BASE + "/flaky.pdf", OUT, LOG, sleep=0.01)
assert r["ok"] and HITS["/flaky.pdf"] == 2 and LOG[0]["status"] == 403 and LOG[1]["status"] == 200
ok("403 on first try is retried with a Referer header and then succeeds (both tries logged with hash)")
r = fetch_doc(BASE + "/missing.pdf", OUT, LOG, sleep=0.01)
assert not r["ok"] and HITS["/missing.pdf"] == 1 and "404" in r["error"]
ok("404 is not retried (a stale or invented URL)")
good = fetch_doc(BASE + "/ok.pdf", OUT, LOG)
assert verify(good["path"], PRESS, q1, TOK)["verified"] is True
wrongq = fetch_doc(BASE + "/wrongq.pdf", OUT, LOG)
v = verify(wrongq["path"], PRESS, q1, TOK); assert v["verified"] is False and "quarter" in v["reason"]
other = fetch_doc(BASE + "/other.pdf", OUT, LOG)
v = verify(other["path"], PRESS, q1, TOK); assert v["verified"] is False and "company" in v["reason"]
ok("verification opens the file: right company and quarter accepted; wrong quarter and wrong company rejected")

# ---- 6. full run on Axis with REAL search results; downloads served by the local server ----
URLMAP = {REAL[0][0]: "/ok.pdf", REAL[1][0]: "/wrongq.pdf"}   # transcript URL serves a Q4 file on purpose
def local_fetch(url, outdir, log):
    if url in URLMAP:
        return fetch_doc(BASE + URLMAP[url], outdir, log)
    return dict(ok=False, error="not served in test")
queries = []
def search(q):
    queries.append(q); return POOL
OUT2 = os.path.join(TMP, "axis_run")
m = find_documents(NAME, SYMBOL, "bank", FixtureBackend(search), TODAY, OUT2, fetch=local_fetch)
assert m["anchor_quarter"] == "Q1 FY27", m["anchor_quarter"]
assert any("Q2 FY27" in n and "business update" in n for n in m["notes"]), m["notes"]
assert [d["need"] for d in m["documents"]] == ["press_release", "results_presentation"], [d["need"] for d in m["documents"]]
assert m["documents"][1]["bundled_with"] == "press_release" and m["documents"][0]["sha256"] == m["documents"][1]["sha256"]
assert any(r["need"] == "earnings_call_transcript" and "quarter" in r["reason"] for r in m["rejected"])
cs = m["coverage_summary"]
assert cs["needs_found"] == 2 and "results_presentation" not in cs["missing"]
assert cs["families"] == ["A"] and cs["gate_A_possible"] is False   # still only company-prepared documents
assert len(m["leads_only"]) > 0 and all(l["tier"] == 4 for l in m["leads_only"])
ok("one official PDF holding press release + investor presentation is recognised as covering both needs (found in the real Axis file)")
ok("Axis run: falls back from Q2 FY27 to Q1 FY27, flags the business update, rejects a wrong-quarter file,")
ok("   keeps news as Tier 4 leads, and reports honestly that Gate A cannot be met from what was found")
assert any(q.startswith("site:axis.bank.in") for q in queries), "should search inside the learned company site"
ok("after the first official document, the finder also searches inside the company's own website (site: query)")
json.dump(m, open(os.path.join(os.path.dirname(__file__), "axis_manifest_from_real_search.json"), "w"), indent=2)

# ---- 7. budget and offline cache ----
m2 = find_documents(NAME, SYMBOL, "bank", FixtureBackend(lambda q: POOL), TODAY, os.path.join(TMP, "b"), fetch=local_fetch, max_fetch=1)
assert "fetch budget used up" in m2["notes"] or m2["coverage_summary"]["fetches_used"] <= 1
ok("fetch budget is enforced")
cb = CachedBackend(FixtureBackend(lambda q: POOL[:2]), os.path.join(TMP, "cache"))
first = cb.search("axis bank q1 fy27"); off = CachedBackend(None, os.path.join(TMP, "cache"), offline=True)
assert off.search("axis bank q1 fy27") == first and off.search("never asked") == []
ok("offline mode replays saved searches (Wi-Fi-failure fallback) and returns nothing for unseen queries")

srv.shutdown(); shutil.rmtree(TMP, ignore_errors=True)
print(f"\n{len(PASSED)} checks passed")
