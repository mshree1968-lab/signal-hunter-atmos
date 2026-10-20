"""
finder.py - the automatic document finder for the Signal Hunter agent.

What it does, in plain words
  1. Works out the company TYPE (bank, NBFC, insurer...) from a short description.
  2. Works out which quarter to look for. It starts with the newest completed quarter and steps
     back if the full results are not published yet (a "business update" is NOT full results).
  3. SEARCHES for each document it needs (never builds URLs by guessing: guessed URLs gave 404s).
  4. Scores every search result: official site? PDF? right document type? right quarter?
     News sites and brokers (Tier 4) are never accepted as evidence; they are kept as leads.
  5. Downloads the best candidates (browser headers, 2 retries, hash, log), then OPENS the file and
     checks the company name and the quarter really appear inside. Wrong file -> rejected.
  6. Writes docs_manifest.json: what was found, what was rejected and why, what is missing.

Every decision is rule-based and logged, so a judge can see why each document was picked.
"""
import hashlib, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request
from dataclasses import dataclass, field
from datetime import date

from sources import (NAME_STOPWORDS, NEEDS, PRESENTATION, PRESS, RATING_DOMAINS,
                     REGULATOR_DOMAINS, TYPE_RULES)

ACCEPT_SCORE = 9.0           # minimum score to even try downloading a candidate
TRY_PER_NEED = 3             # at most this many downloads per need and quarter


def norm(s):
    """Lower-case and keep only letters and digits, so 'Q1 FY27', 'q1-fy27' and 'Q1FY27' all match."""
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


# ----------------------------------------------------------------------------- company type
def classify_type(description):
    """Pick the company type from a business description. Returns (type or None, matched rule)."""
    text = (description or "").lower().replace("non-banking", "nonbanking financial")
    text = text.replace("nonbanking financial", "non-banking financial")
    for kind, patterns in TYPE_RULES:
        for p in patterns:
            if re.search(p, text):
                return kind, p
    return None, None


# ----------------------------------------------------------------------------- quarters
MONTHS = {3: ("March", "mar"), 6: ("June", "jun"), 9: ("September", "sep"), 12: ("December", "dec")}
QEND = {6: 1, 9: 2, 12: 3, 3: 4}


@dataclass
class Period:
    label: str            # e.g. "Q2 FY27"
    end: date             # quarter-end date
    tokens: list          # normalised strings that show this quarter in a title or URL


def make_period(end):
    fy = end.year + 1 if end.month >= 4 else end.year      # Indian FY is named after the March it ends in
    q, yy = QEND[end.month], fy % 100
    full, ab = MONTHS[end.month]
    d, y = end.day, end.year
    toks = [f"q{q}fy{yy:02d}", f"q{q}fy{fy}", f"q{q}fy{fy-1}{yy:02d}",
            f"{d}{full}{y}", f"{full}{d}{y}", f"{d:02d}{end.month:02d}{y}",
            f"{full}{y}", f"{ab}{y}"]
    return Period(f"Q{q} FY{yy:02d}", end, [norm(t) for t in toks])


def quarter_ends(today, back=10, forward=1):
    ends = []
    for y in range(today.year - 4, today.year + 2):
        for m, d in ((3, 31), (6, 30), (9, 30), (12, 31)):
            ends.append(date(y, m, d))
    ends.sort()
    past = [e for e in ends if e <= today]
    future = [e for e in ends if e > today][:forward]
    return past[-back:] + future


def period_ladder(today, n=3):
    """Newest completed quarter first, then older ones."""
    done = [e for e in quarter_ends(today) if e <= today]
    return [make_period(e) for e in reversed(done)][:n]


def wrong_period_tokens(today, target):
    keep = set(target.tokens)
    out = set()
    for e in quarter_ends(today, back=10, forward=1):
        for t in make_period(e).tokens:
            if t not in keep:
                out.add(t)
    return out


# ----------------------------------------------------------------------------- who is who
def company_tokens(name, symbol=""):
    words = re.findall(r"[a-z0-9]+", name.lower())
    ident = {w for w in words if w not in NAME_STOPWORDS and len(w) >= 3}
    initials = "".join(w[0] for w in words if w not in {"of", "the", "and", "limited", "ltd"})
    toks = set(ident)
    if len(initials) >= 3:
        toks.add(initials)
    if symbol:
        toks.add(symbol.lower())
    return {t for t in toks if len(t) >= 3}


def registrable(host):
    parts = host.lower().split(":")[0].split(".")
    if parts and parts[0] == "www":
        parts = parts[1:]
    if len(parts) >= 3 and parts[-2] in {"co", "org", "gov", "ac", "bank", "com", "net"}:
        return ".".join(parts[-3:])
    return ".".join(parts[-2:])


def classify_domain(url, tokens):
    """-> (kind, family). kind: regulator | rating | company | other"""
    dom = registrable(urllib.parse.urlparse(url).netloc)
    if dom in REGULATOR_DOMAINS:
        return "regulator", "B"
    if dom in RATING_DOMAINS:
        return "rating", "C"
    first = dom.split(".")[0]
    if any(t in first for t in tokens):
        return "company", "A"
    return "other", "X"


def doc_class(text):
    """Guess the kind of document from its URL and title (already normalised)."""
    rules = [("business_update", ["businessupdate", "provisional"]),
             ("press_release", ["pressrelease"]),
             ("transcript", ["transcript", "earningscall"]),
             ("rating", ["ratingrationale", "rationale"]),
             ("pillar3", ["pillar3"]),
             ("public_disclosure", ["publicdisclosure"]),
             ("annual_report", ["annualreport", "integratedreport"]),
             ("presentation", ["investorpresentation", "analystpresentation", "earningspresentation", "presentation"]),
             ("results", ["financialresult", "unauditedfinancial", "resultsfiling"])]
    for kind, keys in rules:
        if any(k in text for k in keys):
            return kind
    return "unknown"


# ----------------------------------------------------------------------------- scoring
@dataclass
class Candidate:
    url: str
    title: str = ""
    snippet: str = ""
    kind: str = ""
    family: str = ""
    dclass: str = ""
    score: float = 0.0
    why: list = field(default_factory=list)


def full_name(name):
    """'Bajaj Finance Limited' -> 'bajajfinance' (used to tell a company from its group companies)."""
    words = [w for w in re.findall(r"[a-z0-9]+", name.lower()) if w not in {"limited", "ltd", "the"}]
    return "".join(words)


# Words that mark a DIFFERENT group company when they sit next to the name (Bajaj HOUSING Finance,
# Bajaj Financial SECURITIES...). Only penalised if the word is not part of the company's own name.
SIBLING_WORDS = ["housing", "securities", "broking", "insurance", "life", "general", "allianz",
                 "assetmanagement", "amc", "mutualfund", "capital", "ventures", "holdings", "financial"]


def sibling_word(text, name):
    own = full_name(name)
    first = own[:max(4, len(re.findall(r"[a-z0-9]+", name.lower())[0]))]
    for w in SIBLING_WORDS:
        if w not in own and (first + w) in text:
            return w
    return None


def score_candidate(c, need, period, tokens, wrong_tokens, name=""):
    c.kind, c.family = classify_domain(c.url, tokens)
    ut = norm(c.url + " " + c.title)
    c.dclass = doc_class(ut)
    s, why = 0.0, []
    if name:
        sib = sibling_word(ut, name)
        if sib:
            s -= 8; why.append(f"looks like a group company ('{sib}'), not {name}")
        elif full_name(name) in ut:
            s += 2; why.append("full company name in URL/title")
    if c.kind == "other":
        s -= 10; why.append("news/broker/aggregator site (Tier 4: lead only)")
    else:
        s += 5; why.append(f"{c.kind} site")
    path = urllib.parse.urlparse(c.url).path.lower()
    if path.endswith(".pdf"):
        s += 2; why.append("PDF")
    elif need["allow_html"] and c.kind == "rating":
        s += 2; why.append("HTML ok for rating rationale")
    if c.dclass == need["doc_class"]:
        s += 4; why.append(f"document type matches ({c.dclass})")
    elif c.dclass != "unknown":
        s -= 6; why.append(f"wrong document type ({c.dclass}, need {need['doc_class']})")
    if need["doc_class"] == "rating" and c.kind != "rating":
        s -= 6; why.append("rating need but not a rating-agency site")
    if need["per_quarter"] and period:
        if any(t in ut + norm(c.snippet[:200]) for t in period.tokens):
            s += 4; why.append(f"quarter matches ({period.label})")
        elif any(t in ut for t in wrong_tokens):
            s -= 4; why.append("different quarter in URL/title")
    if any(t in ut for t in tokens):
        s += 1; why.append("company name in URL/title")
    if "revised" in ut or "updated" in ut:
        s += 0.5; why.append("revised/updated version preferred")
    c.score, c.why = round(s, 1), why
    return c


# ----------------------------------------------------------------------------- search backends
class FixtureBackend:
    """For tests and offline demos: returns saved results."""
    def __init__(self, func):
        self.func = func
    def search(self, query, n=10):
        return self.func(query)[:n]


class CachedBackend:
    """Wraps any backend. Every query is saved to disk; offline=True replays only from disk.
    This is the 'Wi-Fi fails' fallback from the finals run-book."""
    def __init__(self, inner, cache_dir, offline=False):
        self.inner, self.dir, self.offline = inner, os.path.join(cache_dir, "search"), offline
        os.makedirs(self.dir, exist_ok=True)
    def search(self, query, n=10):
        path = os.path.join(self.dir, hashlib.sha1(query.encode()).hexdigest()[:16] + ".json")
        if os.path.exists(path):
            return json.load(open(path, encoding="utf-8"))[:n]
        if self.offline:
            return []
        res = self.inner.search(query, n)
        json.dump(res, open(path, "w", encoding="utf-8"), ensure_ascii=False)
        return res


class DDGBackend:
    """Free web search with no API key. Uses the 'ddgs' package if installed, else DuckDuckGo's
    plain HTML page. Not tested live from the build sandbox (no internet there): test on your PC."""
    UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
          "Chrome/124.0 Safari/537.36")
    def search(self, query, n=10):
        try:
            from ddgs import DDGS
            return [dict(url=r["href"], title=r.get("title", ""), snippet=r.get("body", ""))
                    for r in DDGS().text(query, max_results=n)]
        except ImportError:
            pass
        url = "https://html.duckduckgo.com/html/?q=" + urllib.parse.quote(query)
        req = urllib.request.Request(url, headers={"User-Agent": self.UA})
        html = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        out = []
        for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.S):
            href = m.group(1)
            if "uddg=" in href:
                href = urllib.parse.unquote(href.split("uddg=")[1].split("&")[0])
            title = re.sub(r"<[^>]+>", "", m.group(2))
            out.append(dict(url=href, title=title, snippet=""))
        return out[:n]


# ----------------------------------------------------------------------------- download + verify
BROWSER = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
           "Chrome/124.0 Safari/537.36")


def fetch_doc(url, outdir, log, retries=2, sleep=0.5):
    """Download with browser headers. 403/429/5xx are retried; 404 is not (stale or guessed URL)."""
    os.makedirs(os.path.join(outdir, "docs"), exist_ok=True)
    last_err = None
    for attempt in range(retries + 1):
        headers = {"User-Agent": BROWSER, "Accept": "application/pdf,text/html,*/*"}
        if attempt > 0:
            p = urllib.parse.urlparse(url)
            headers["Referer"] = f"{p.scheme}://{p.netloc}/"
        entry = dict(ts=time.strftime("%Y-%m-%d %H:%M:%S"), url=url, attempt=attempt + 1)
        try:
            resp = urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=30)
            data = resp.read()
            sha = hashlib.sha256(data).hexdigest()
            ext = ".pdf" if data[:4] == b"%PDF" else ".html"
            path = os.path.join(outdir, "docs", f"{sha[:8]}{ext}")
            open(path, "wb").write(data)
            entry.update(status=resp.status, bytes=len(data), sha256=sha, saved=path)
            log.append(entry)
            return dict(ok=True, path=path, sha256=sha, bytes=len(data), is_pdf=ext == ".pdf")
        except urllib.error.HTTPError as e:
            entry.update(status=e.code, error=str(e))
            last_err = f"HTTP {e.code}"
            log.append(entry)
            if e.code == 404:
                return dict(ok=False, error="HTTP 404 (URL stale or invented)")
        except Exception as e:                      # timeouts, DNS, connection resets
            entry.update(status=None, error=repr(e))
            last_err = repr(e)
            log.append(entry)
        time.sleep(sleep * (attempt + 1))
    return dict(ok=False, error=f"gave up after {retries + 1} tries: {last_err}")


def read_text(path, max_pages=4):
    if path.endswith(".pdf"):
        try:
            from pypdf import PdfReader
        except ImportError:
            return None, None
        r = PdfReader(path)
        txt = " ".join((r.pages[i].extract_text() or "") for i in range(min(max_pages, len(r.pages))))
        return txt, len(r.pages)
    html = open(path, "rb").read().decode("utf-8", "ignore")
    return re.sub(r"<[^>]+>", " ", html), None


def covers_presentation(path):
    """Real-world finding (Axis Bank, Q1 FY27): ONE official PDF can hold the exchange cover letter,
    the press release AND the full investor presentation. If a long PDF contains the words
    'Investor Presentation', it also satisfies the presentation need."""
    if not path.endswith(".pdf"):
        return False
    try:
        from pypdf import PdfReader
        r = PdfReader(path)
        if len(r.pages) < 15:
            return False
        txt = " ".join((p.extract_text() or "") for p in r.pages[:60])
        return "investorpresentation" in norm(txt)
    except Exception:
        return False


def verify(path, need, period, tokens, name=""):
    """Open the file and check it is really about this company and quarter."""
    text, pages = read_text(path)
    if text is None:
        return dict(verified=None, reason="pypdf not installed: cannot verify (install pypdf)")
    if len(text.strip()) < 200 and path.endswith(".pdf"):
        return dict(verified=False, reason="no extractable text (scanned file? needs OCR)", pages=pages)
    n = norm(text[:30000])
    if not any(t in n for t in tokens):
        return dict(verified=False, reason="company name not found inside the file", pages=pages)
    if name:
        own = full_name(name)
        if own not in n:
            return dict(verified=False, reason=f"full name '{name}' not found inside the file", pages=pages)
        sib = sibling_word(n, name)
        if sib:
            first = own[:max(4, len(re.findall(r'[a-z0-9]+', name.lower())[0]))]
            if n.count(first + sib) > n.count(own):
                return dict(verified=False, reason=f"file is mainly about a group company ('{sib}')", pages=pages)
    if need["per_quarter"] and period and not any(t in n for t in period.tokens):
        return dict(verified=False, reason=f"quarter {period.label} not found inside the file", pages=pages)
    return dict(verified=True, reason="company and quarter found inside the file", pages=pages)


# ----------------------------------------------------------------------------- the main routine
def find_documents(name, symbol, archetype, backend, today, outdir, fetch=None,
                   max_fetch=25, ladder_n=3, needs=None):
    fetch = fetch or fetch_doc
    needs = needs or NEEDS[archetype]     # express mode passes a shorter list
    tokens = company_tokens(name, symbol)
    ladder = period_ladder(today, ladder_n)
    log, seen_leads = [], set()
    m = dict(company=name, symbol=symbol, archetype=archetype, as_of=today.isoformat(),
             quarters_tried_newest_first=[p.label for p in ladder], anchor_quarter=None,
             documents=[], rejected=[], leads_only=[], notes=[], coverage=[])
    used = {"fetches": 0}
    learned = {"dom": None}          # the company's own website, learned from the first official document

    def try_need(need, period):
        wrong = wrong_period_tokens(today, period) if period else set()
        pool, urls = [], set()
        queries = [q.format(name=name, period=period.label if period else "") for q in need["queries"]]
        if learned["dom"]:           # search inside the company's own site as well
            queries.append(f"site:{learned['dom']} " + queries[0])
        for query in queries:
            for r in backend.search(query):
                if r["url"] not in urls:
                    urls.add(r["url"])
                    pool.append(score_candidate(Candidate(r["url"], r.get("title", ""), r.get("snippet", "")),
                                                need, period, tokens, wrong, name))
        pool.sort(key=lambda c: c.score, reverse=True)
        for c in pool:                                   # keep news/updates as leads, never as evidence
            if c.kind == "other" and c.url not in seen_leads and len(m["leads_only"]) < 12:
                seen_leads.add(c.url)
                m["leads_only"].append(dict(url=c.url, title=c.title, tier=4, why="lead only"))
            if c.dclass == "business_update" and period and any(t in norm(c.url + c.title) for t in period.tokens):
                note = f"{period.label}: only a provisional business update seen ({c.url}); not full results"
                if note not in m["notes"]:
                    m["notes"].append(note)
        tries = 0
        for c in pool:
            if c.score < ACCEPT_SCORE or tries >= TRY_PER_NEED:
                continue
            if used["fetches"] >= max_fetch:
                m["notes"].append("fetch budget used up")
                break
            tries += 1; used["fetches"] += 1
            got = fetch(c.url, outdir, log)
            if not got["ok"]:
                m["rejected"].append(dict(need=need["key"], url=c.url, score=c.score, reason=got["error"]))
                continue
            if need["doc_class"] != "rating" and not need["allow_html"] and not got["is_pdf"]:
                m["rejected"].append(dict(need=need["key"], url=c.url, score=c.score,
                                          reason="expected a PDF but got a web page (login or error page?)"))
                continue
            v = verify(got["path"], need, period, tokens, name)
            if v["verified"] is False:
                m["rejected"].append(dict(need=need["key"], url=c.url, score=c.score, reason=v["reason"]))
                continue
            doc = dict(need=need["key"], url=c.url, quarter=period.label if period else None,
                       tier=need["tier"], family=c.family, score=c.score, why=c.why,
                       sha256=got["sha256"], file=got["path"], pages=v.get("pages"),
                       verified=v["verified"], verify_note=v["reason"])
            m["documents"].append(doc)
            if c.kind == "company" and not learned["dom"]:
                learned["dom"] = registrable(urllib.parse.urlparse(c.url).netloc)
            keys = {n["key"] for n in needs}
            have = {d["need"] for d in m["documents"]}
            if need["key"] == "press_release" and "results_presentation" in keys - have \
                    and covers_presentation(got["path"]):
                bundled = dict(doc, need="results_presentation", bundled_with="press_release",
                               why=doc["why"] + ["same PDF also contains the investor presentation"])
                m["documents"].append(bundled)
            return doc
        best = pool[0] if pool else None
        m["coverage"].append(dict(need=need["key"], quarter=period.label if period else None, found=False,
                                  best_candidate=(best.url, best.score, best.why) if best else None))
        return None

    # step 1: find the newest quarter for which the full results are published
    for p in ladder:
        hit = None
        for need in (PRESENTATION, PRESS):
            if need in needs:
                hit = try_need(need, p)
                if hit:
                    break
        if hit:
            m["anchor_quarter"] = p.label
            anchor = p
            break
    else:
        anchor = None
        m["notes"].append("no full-results document found for any quarter tried")

    # step 2: every other document, using the same quarter so numbers line up
    done = {d["need"] for d in m["documents"]}
    for need in needs:
        if need["key"] in done:
            continue
        periods = ([anchor] if anchor else ladder) if need["per_quarter"] else [None]
        for p in periods:
            if try_need(need, p):
                break

    found = {d["need"] for d in m["documents"]}
    seen_cov, cov = set(), []
    for c in m["coverage"]:
        k = (c["need"], c["quarter"])
        if c["need"] not in found and k not in seen_cov:
            seen_cov.add(k); cov.append(c)
    m["coverage"] = cov
    m["coverage_summary"] = dict(
        needs_total=len(needs), needs_found=len(found),
        missing=[n["key"] for n in needs if n["key"] not in found],
        families=sorted({d["family"] for d in m["documents"]}),
        lowest_tier=min([d["tier"] for d in m["documents"]], default=None),
        gate_A_possible=len({d["family"] for d in m["documents"]}) >= 2 and
                        any(d["tier"] <= 2 for d in m["documents"]),
        fetches_used=used["fetches"])
    os.makedirs(outdir, exist_ok=True)
    json.dump(m, open(os.path.join(outdir, "docs_manifest.json"), "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    json.dump(log, open(os.path.join(outdir, "fetch_log.json"), "w", encoding="utf-8"), indent=2)
    return m


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description="Find the public documents for a Track A company")
    ap.add_argument("--company", required=True)
    ap.add_argument("--symbol", default="")
    ap.add_argument("--about", default="", help="short business description, used to pick the company type")
    ap.add_argument("--type", default="", help="override the company type: " + ", ".join(NEEDS))
    ap.add_argument("--today", default="", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--out", default="run_out")
    ap.add_argument("--offline", action="store_true", help="replay cached searches only")
    a = ap.parse_args(argv)
    today = date.fromisoformat(a.today) if a.today else date.today()
    backend = CachedBackend(DDGBackend(), a.out, offline=a.offline)
    kind = a.type
    if not kind:
        desc = a.about or " ".join(r["title"] + " " + r.get("snippet", "")
                                   for r in backend.search(f"{a.company} company business profile", 5))
        kind, rule = classify_type(desc)
        if not kind:
            sys.exit("Could not decide the company type. Pass --type or a clearer --about.")
        print(f"company type: {kind} (matched rule {rule!r})")
    m = find_documents(a.company, a.symbol, kind, backend, today, a.out)
    print(json.dumps(m["coverage_summary"], indent=2))
    for d in m["documents"]:
        print(f"  FOUND {d['need']:<22} {d['quarter'] or '-':<8} tier {d['tier']} fam {d['family']}  {d['url']}")
    for c in m["coverage_summary"]["missing"]:
        print(f"  MISSING {c}")


if __name__ == "__main__":
    main(sys.argv[1:])
