"""Finding and downloading documents.
Main route: the search-based finder (finder.py). Fallback: the hand-typed URLs in retrieval.py."""
import hashlib, json, re, urllib.error, urllib.request
from datetime import date

from agent import DATA

HEADERS = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
           "Accept": "application/pdf,text/html,*/*"}

# finder.py knows these company types; other archetypes borrow the lender document list
FINDER_TYPE = {"bank": "bank", "nbfc": "nbfc", "hfc": "nbfc", "government_lender": "nbfc",
               "card_specialty": "nbfc", "holding": "holding", "life": "life",
               "general": "general", "exchange": "exchange", "amc": "amc"}

DOCS = []   # every document available to the agent this run: id, url, file, tier, family, ...


def _slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def _register(doc):
    for d in DOCS:
        if d.get("file") and d.get("file") == doc.get("file"):
            return d
    doc["id"] = f"D{len(DOCS) + 1:02d}"
    DOCS.append(doc)
    json.dump(DOCS, open(DATA / "documents.json", "w", encoding="utf-8"), indent=2, ensure_ascii=False)
    return doc


def find_documents(company, symbol, archetype, mode="express"):
    """Search for the company's documents, download and verify them. Returns a short summary."""
    import finder, sources
    from agent.llm import search_backend
    kind = FINDER_TYPE.get(archetype)
    if not kind:
        return {"error": f"unknown archetype '{archetype}'. Use one of {sorted(FINDER_TYPE)}"}
    out = DATA / f"run_{_slug(company)}"
    backend = finder.CachedBackend(search_backend(), str(out))
    needs = sources.NEEDS[kind]
    if mode == "express":     # express: latest presentation + results + one rating report
        keep = {"results_presentation", "press_release", "results_filing", "rating_rationale"}
        needs = [n for n in needs if n["key"] in keep]
    m = finder.find_documents(company, symbol, kind, backend, date.today(), str(out),
                              max_fetch=8 if mode == "express" else 25,
                              ladder_n=2 if mode == "express" else 3, needs=needs)
    docs = []
    for d in m["documents"]:
        reg = _register(dict(url=d["url"], file=d["file"], need=d["need"], quarter=d["quarter"],
                             tier=d["tier"], family=d["family"], pages=d.get("pages"),
                             route="search", sha256=d["sha256"][:16]))
        docs.append({k: reg.get(k) for k in ("id", "need", "quarter", "tier", "family", "pages", "url", "file")})
    result = dict(route="search-based finder", anchor_quarter=m["anchor_quarter"], documents=docs,
                  missing=m["coverage_summary"]["missing"], rejected=len(m["rejected"]),
                  notes=m["notes"][:5], gate_A_possible=m["coverage_summary"]["gate_A_possible"])
    if not docs:                                     # fallback only: unverified hand-typed URLs
        import retrieval
        log = retrieval.fetch_by_template(company, archetype, cache_dir=str(out / "fallback"))
        for e in log:
            if e.get("path") and open(e["path"], "rb").read(4) == b"%PDF":
                reg = _register(dict(url=e["url"], file=e["path"], need=e["note"], quarter=None,
                                     tier=e["tier"], family=e["family"], route="fallback-url"))
                docs.append({k: reg.get(k) for k in ("id", "need", "tier", "family", "url", "file")})
        result.update(route="fallback URL list (search found nothing)", documents=docs,
                      fallback_log=[{k: e[k] for k in ("url", "status", "bytes")} for e in log])
    return result


def fetch_url(url, timeout=30):
    """Download one URL. PDFs are saved and registered as documents; web pages return trimmed text."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            data = r.read()
    except urllib.error.HTTPError as e:
        return {"status": f"HTTP-{e.code}", "url": url}
    except Exception as e:
        return {"status": type(e).__name__, "url": url}
    if data[:4] == b"%PDF":
        p = DATA / "docs"
        p.mkdir(parents=True, exist_ok=True)
        f = p / f"{hashlib.sha256(data).hexdigest()[:12]}.pdf"
        f.write_bytes(data)
        try:
            from pypdf import PdfReader
            pages = len(PdfReader(str(f)).pages)
        except Exception:
            pages = None
        import finder
        _, fam = finder.classify_domain(url, set())
        reg = _register(dict(url=url, file=str(f), need="fetched", quarter=None,
                             tier=1 if fam == "B" else 3 if fam == "C" else 2,
                             family=fam if fam != "X" else "A?", pages=pages, route="fetch_url"))
        return {"status": "PDF saved", "doc_id": reg["id"], "file": str(f), "pages": pages}
    text = re.sub(r"<script.*?</script>|<style.*?</style>", " ", data.decode("utf-8", "replace"), flags=re.S)
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    links = re.findall(r'href="([^"]+\.pdf[^"]*)"', data.decode("utf-8", "replace"))[:15]
    return {"status": "HTML", "url": url, "text": text[:4000], "pdf_links": links}
