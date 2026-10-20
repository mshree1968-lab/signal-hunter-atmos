"""
sources.py - what documents to look for, by company TYPE, and which websites to trust.
No company names, tickers or URLs for specific companies live here (hard-coding is banned by the brief).

Tier / family (from the Playbook):
  Tier 1 = audited filings, exchange/regulator documents    -> family B
  Tier 2 = company-prepared (presentations, press releases) -> family A
  Tier 3 = independent cross-check (rating agencies)        -> family C
  Tier 4 = news / brokers / aggregators: leads only, never evidence
"""

# Websites that are exchange or regulator sources (Tier 1, family B)
REGULATOR_DOMAINS = {
    "nseindia.com", "bseindia.com", "sebi.gov.in", "rbi.org.in", "irdai.gov.in",
    "londonstockexchange.com", "mca.gov.in", "amfiindia.com",
}
# Rating agencies (Tier 3, family C)
RATING_DOMAINS = {
    "crisil.com", "icra.in", "careratings.com", "careedge.in",
    "indiaratings.co.in", "acuite.in", "brickworkratings.com",
}

# Words that carry no identity when we match a company name against a website name
NAME_STOPWORDS = {
    "limited", "ltd", "the", "of", "and", "india", "indian", "company", "corporation",
    "corp", "private", "pvt", "financial", "finance", "services", "service", "bank",
    "banking", "insurance", "life", "general", "holdings", "holding", "investment",
    "investments", "co", "inc", "housing", "capital", "fund", "funds",
}

# Each need: key, what kind of document, tier, family, whether it belongs to a quarter,
# search queries ({name} and {period} are filled in), and the document classes we accept.
def _n(key, doc_class, tier, family, per_quarter, queries, required=True, allow_html=False):
    return dict(key=key, doc_class=doc_class, tier=tier, family=family, per_quarter=per_quarter,
                queries=queries, required=required, allow_html=allow_html)

PRESENTATION = _n("results_presentation", "presentation", 2, "A", True,
    ["{name} investor presentation {period}", "{name} analyst presentation {period} pdf"])
PRESS = _n("press_release", "press_release", 2, "A", True,
    ["{name} press release financial results {period}"])
RESULTS = _n("results_filing", "results", 1, "B", True,
    ["{name} unaudited financial results {period} stock exchange filing"], required=False)
TRANSCRIPT = _n("earnings_call_transcript", "transcript", 2, "A", True,
    ["{name} earnings call transcript {period}"], required=False)
ANNUAL = _n("annual_report", "annual_report", 1, "A", False,
    ["{name} annual report 2025-26 pdf", "{name} annual report notes to accounts"])
RATING = _n("rating_rationale", "rating", 3, "C", False,
    ["{name} rating rationale crisil", "{name} rating rationale icra care"], allow_html=True)
PILLAR3 = _n("pillar3", "pillar3", 1, "B", True,
    ["{name} pillar 3 disclosures {period}"], required=False)
PUBLIC_DISC = _n("public_disclosures", "public_disclosure", 1, "B", True,
    ["{name} public disclosures {period} irdai"], required=False)

NEEDS = {
    "bank":     [PRESENTATION, PRESS, RESULTS, TRANSCRIPT, ANNUAL, RATING, PILLAR3],
    "nbfc":     [PRESENTATION, PRESS, RESULTS, TRANSCRIPT, ANNUAL, RATING],
    "holding":  [PRESENTATION, PRESS, RESULTS, ANNUAL, RATING],
    "life":     [PRESENTATION, PRESS, PUBLIC_DISC, ANNUAL],
    "general":  [PRESENTATION, PRESS, PUBLIC_DISC, ANNUAL],
    "exchange": [PRESENTATION, PRESS, RESULTS, ANNUAL],
    "amc":      [PRESENTATION, PRESS, RESULTS, ANNUAL],
}

# Keyword rules to decide the company type from a short business description.
# Order matters: the first rule that matches wins.
TYPE_RULES = [
    ("life",     [r"life insurance", r"life insurer"]),
    ("general",  [r"general insurance", r"non-life insur", r"motor insurance", r"general insurer"]),
    ("exchange", [r"stock exchange", r"bourse", r"clearing corporation", r"depository"]),
    ("amc",      [r"asset management", r"mutual fund house", r"\bamc\b"]),
    ("holding",  [r"holding company", r"core investment company", r"financial holding"]),
    ("nbfc",     [r"non-banking financial", r"\bnbfc\b", r"housing finance", r"gold loan", r"vehicle finance"]),
    ("bank",     [r"\bbank\b", r"scheduled commercial bank", r"small finance bank"]),
]
