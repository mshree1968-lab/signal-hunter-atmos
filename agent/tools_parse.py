"""Reading PDFs in small pieces, so the model never loads a whole report at once."""
import re
from functools import lru_cache

MAX_PAGES_PER_CALL = 4
MAX_CHARS_PER_PAGE = 3500


@lru_cache(maxsize=16)
def _pages(path):
    from pypdf import PdfReader
    return tuple((p.extract_text() or "") for p in PdfReader(path).pages)


def _resolve(doc):
    """Accept a document id (D01) or a file path."""
    from agent.tools_web import DOCS
    for d in DOCS:
        if doc in (d["id"], d.get("file")):
            return d["file"]
    return doc


def page_text(doc, page):
    pages = _pages(_resolve(doc))
    return pages[page - 1] if 1 <= page <= len(pages) else ""


def read_pdf(doc, pages="1-3"):
    """pages like '5' or '5-8'. At most 4 pages per call."""
    path = _resolve(doc)
    allp = _pages(path)
    a, _, b = str(pages).partition("-")
    start = max(1, int(a)); end = min(len(allp), int(b or a), start + MAX_PAGES_PER_CALL - 1)
    return {"doc": doc, "page_count": len(allp),
            "pages": [{"page": i, "text": re.sub(r"[ \t]+", " ", allp[i - 1])[:MAX_CHARS_PER_PAGE]}
                      for i in range(start, end + 1)]}


def find_in_pdf(doc, keywords, max_hits=10):
    """Find which pages mention any keyword. Returns page numbers with a short snippet each."""
    if isinstance(keywords, str):              # a single string must not be split into letters
        keywords = [keywords]
    path = _resolve(doc)
    allp = _pages(path)
    hits = []
    for i, t in enumerate(allp, 1):
        low = t.lower()
        for k in keywords:
            j = low.find(k.lower())
            if j >= 0:
                hits.append({"page": i, "keyword": k,
                             "snippet": re.sub(r"\s+", " ", t[max(0, j - 120): j + 220])})
                break
        if len(hits) >= max_hits:
            break
    return {"doc": doc, "page_count": len(allp), "hits": hits}
