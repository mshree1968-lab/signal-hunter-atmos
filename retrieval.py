"""FALLBACK ONLY. Archetype + named-company URL templates.
These URLs were typed by hand and were NOT verified. The main route is the search-based
finder (finder.py). The agent uses this file only when the finder returns no documents.
"""
import urllib.request, urllib.error, hashlib, json
from datetime import datetime, timezone
from pathlib import Path

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"),
    "Referer": "https://www.google.com/",
}

NAMED = {
    "Bajaj Finance": [
        ("A", 2, "https://cms-assets.bajajfinserv.in/is/content/bajajfinance/bajaj-finance-q1-fy27-investor-presentation?fmt=pdf&scl=1", "Q1 FY27 presentation"),
        ("A", 1, "https://www.bajajfinserv.in/investors/annual-reports", "annual report index"),
        ("A", 2, "https://www.bajajfinserv.in/investors/financial-results", "quarterly results"),
        ("C", 3, "https://www.crisil.com/mnt/winshare/Ratings/RatingList/RatingDocs/BajajFinanceLimited_September%2017_%202026_RR_404898.html", "CRISIL rationale"),
    ],
    "HDFC Bank": [
        ("A", 2, "https://www.hdfc.bank.in/content/dam/hdfcbankpws/in/en/pdf/about-us/financial-results/2026-2027/quarter-1/q1fy27-earnings-presentation.pdf", "Q1 FY27 earnings"),
        ("A", 1, "https://www.hdfc.bank.in/investor-relations/financial-results", "quarterly results"),
        ("A", 1, "https://www.hdfc.bank.in/investor-relations/annual-reports", "annual report"),
    ],
    "HDFC Life": [
        ("A", 2, "https://www.hdfclife.com/content/dam/hdfclifeinsurancecompany/about-us/pdf/investor-relations/financial-information/investor-presentation/HDFC-Life-Q1-FY2027-Investor-Presentation.pdf", "Q1 FY27 presentation"),
        ("A", 2, "https://www.hdfclife.com/content/dam/hdfclifeinsurancecompany/about-us/pdf/investor-relations/financial-information/Quarterly-financial-results/HDFC-Life-Q1-FY2027-Press-Release.pdf", "Q1 FY27 press release"),
        ("A", 1, "https://www.hdfclife.com/investor-relations/regulatory-disclosure", "IRDAI disclosures"),
    ],
    "State Bank of India": [
        ("A", 2, "https://sbi.bank.in/documents/17836/1275616/07082026_SBI+Analyst+Presentation+Q1FY27.pdf/6e4ca530-1666-574e-22fb-f9e19d553ef5?t=1786091443352", "Q1 FY27 analyst presentation"),
        ("A", 1, "https://sbi.bank.in/web/investor-relations/financial-results", "financial results index"),
        ("A", 1, "https://sbi.bank.in/web/investor-relations/annual-reports", "annual report"),
    ],
    "Cholamandalam Investment": [
        ("A", 2, "https://files.cholamandalam.com/cholafhl/CFHL_Investor_presentation_Jun26_25591edd42.pdf", "Q1 FY27 presentation"),
        ("A", 1, "https://www.cholamandalam.com/investors/financials", "financials index"),
    ],
    "Bajaj Finserv": [
        ("A", 2, "https://www.bajajfinserv.in/investors/investor-presentations", "investor presentations"),
        ("A", 1, "https://www.bajajfinserv.in/investors/annual-reports", "annual report"),
    ],
    "BSE Ltd": [
        ("A", 1, "https://www.bseindia.com/corporates/ann.html", "corporate announcements"),
        ("A", 2, "https://www.bseindia.com/Static/About/Investor_Relations.aspx", "IR page"),
        ("A", 1, "https://www.bseindia.com/Static/About/Annual_Report.aspx", "annual report"),
        ("D", 1, "https://www.sebi.gov.in/", "SEBI data"),
    ],
    "ICICI Lombard": [
        ("A", 2, "https://www.icicilombard.com/investor-relations", "IR page"),
        ("A", 1, "https://www.icicilombard.com/docs/default-source/investor-relations", "financial results"),
        ("A", 1, "https://www.icicilombard.com/investor-relations/annual-reports", "annual report"),
    ],
    "HDFC AMC": [
        ("A", 2, "https://www.hdfcfund.com/about-us/investor-relations", "IR page"),
        ("A", 1, "https://www.hdfcfund.com/about-us/investor-relations/annual-report", "annual report"),
        ("D", 1, "https://www.amfiindia.com/", "AMFI data"),
    ],
    "Muthoot Finance": [
        ("A", 2, "https://www.muthootfinance.com/investor-relations/investor-presentations", "investor presentations"),
        ("A", 1, "https://www.muthootfinance.com/investor-relations/financial-results", "financial results"),
        ("A", 1, "https://www.muthootfinance.com/investor-relations/annual-reports", "annual report"),
    ],
    "Bank of Baroda": [
        ("A", 1, "https://www.bankofbaroda.in/investor-relations/financial-results", "financial results"),
        ("A", 2, "https://www.bankofbaroda.in/investor-relations/investor-presentations", "investor presentations"),
        ("A", 1, "https://www.bankofbaroda.in/investor-relations/annual-reports", "annual report"),
    ],
    "Shriram Finance": [
        ("A", 2, "https://www.shriramfinance.in/investor-relations/investor-presentations", "investor presentations"),
        ("A", 1, "https://www.shriramfinance.in/investor-relations/financials", "financials"),
        ("A", 1, "https://www.shriramfinance.in/investor-relations/annual-reports", "annual report"),
    ],
    "Axis Bank": [
        ("A", 2, "https://www.axisbank.com/investor-relations/financial-results", "financial results"),
        ("A", 1, "https://www.axisbank.com/investor-relations/annual-reports", "annual report"),
    ],
    "ICICI Bank": [
        ("A", 2, "https://www.icicibank.com/ms/investor-relations/annual-reports", "annual report"),
        ("A", 1, "https://www.icicibank.com/ms/investor-relations/financial-results", "financial results"),
    ],
    "Kotak Mahindra Bank": [
        ("A", 2, "https://www.kotak.com/en/investor-relations/financial-results.html", "financial results"),
        ("A", 1, "https://www.kotak.com/en/investor-relations/annual-reports.html", "annual report"),
    ],
    "SBI Life": [
        ("A", 2, "https://www.sbilife.co.in/en/about-us/investors", "IR page"),
        ("A", 1, "https://www.sbilife.co.in/en/about-us/investors/financial-results", "financial results"),
    ],
    "Jio Financial Services": [
        ("A", 2, "https://www.jfs.in/investors", "IR page"),
        ("A", 1, "https://www.jfs.in/investors/financial-results", "financial results"),
    ],
}

FALLBACK = {
    "bank": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE"),
             ("D", 1, "https://rbi.org.in/", "RBI")],
    "nbfc": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE"),
             ("C", 3, "https://www.crisil.com/en/home/our-businesses/ratings.html", "CRISIL")],
    "hfc":  [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE"),
             ("D", 1, "https://www.nhb.org.in/", "NHB")],
    "government_lender": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE"),
             ("C", 3, "https://www.icra.in/Rating/", "ICRA")],
    "card_specialty": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE")],
    "life": [("A", 1, "https://irdai.gov.in/web/guest/annual-reports", "IRDAI"),
             ("A", 2, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE")],
    "general": [("A", 1, "https://irdai.gov.in/web/guest/annual-reports", "IRDAI"),
             ("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE")],
    "exchange": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE"),
             ("D", 1, "https://www.sebi.gov.in/", "SEBI")],
    "amc": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE"),
             ("D", 1, "https://www.amfiindia.com/", "AMFI")],
    "holding": [("A", 1, "https://www.nseindia.com/companies-listing/corporate-filings-financial-results", "NSE")],
}

def _slug(name): return name.lower().replace(" ", "-").replace(".", "").replace(",", "")

def build_urls(company_name, archetype):
    urls = list(NAMED.get(company_name, []))
    for entry in FALLBACK.get(archetype, FALLBACK["nbfc"]):
        if entry not in urls:
            urls.append(entry)
    return urls

def fetch(url, retries=2, timeout=30):
    for attempt in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return r.read(), "OK"
        except urllib.error.HTTPError as e:
            if e.code in (403, 404) and attempt < retries: continue
            return b"", f"HTTP-{e.code}"
        except urllib.error.URLError:
            if attempt < retries: continue
            return b"", "URLError"
        except Exception as e:
            return b"", type(e).__name__
    return b"", "BLOCKED"

def fetch_by_template(company_name, archetype, cache_dir="data/docs"):
    Path(cache_dir).mkdir(parents=True, exist_ok=True)
    log = []
    for family, tier, url, note in build_urls(company_name, archetype):
        data, status = fetch(url)
        entry = {"family": family, "tier": tier, "url": url, "note": note,
                 "status": status, "bytes": len(data),
                 "fetched_at": datetime.now(timezone.utc).isoformat()}
        if data:
            h = hashlib.sha256(data).hexdigest()[:16]
            p = Path(cache_dir) / f"{_slug(company_name)}_{family}_{tier}_{h}.bin"
            p.write_bytes(data)
            entry["sha256"] = h
            entry["path"] = str(p)
        log.append(entry)
    return log

def coverage_log_summary(log):
    read = [x for x in log if x["bytes"] > 0]
    return {"attempted": len(log), "read": len(read),
            "blocked": len(log) - len(read),
            "families_read": sorted(set(x["family"] for x in read)),
            "has_tier1_or_2": any(x["tier"] in (1, 2) and x["bytes"] > 0 for x in log),
            "status": "OK" if read else "NO_DOCUMENTS_FETCHED"}
