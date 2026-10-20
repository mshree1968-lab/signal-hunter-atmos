# Document finder (Signal Hunter, Track A)

Finds the public documents for ANY Track A company, with no company names in the code.

## Files
- `sources.py`   what to look for per company type; which sites are Tier 1 / 3 / 4
- `finder.py`    quarter ladder, search, ranking, download (retries, hashes, log), open-and-verify
- `test_finder.py`  15 offline checks; uses real Axis Bank search results as fixtures
- `axis_manifest_from_real_search.json`  the manifest the test run produced

## Run the tests (no internet needed)
    pip install pypdf reportlab
    python test_finder.py

## Run it on a company (needs internet; on your own PC)
    pip install pypdf ddgs
    python finder.py --company "Axis Bank Limited" --symbol AXISBANK --about "private sector bank" --out run_axis
    python finder.py --company "Axis Bank Limited" --symbol AXISBANK --out run_axis --offline    # replay saved searches

Output in `run_axis/`: `docs_manifest.json` (found / rejected / missing / leads), `fetch_log.json`, `docs/` (files), `search/` (cache).

## How it decides
1. Newest completed quarter first (20 Oct 2026 -> Q2 FY27, then Q1 FY27, then Q4 FY26). A "business update" is not full results.
2. Every search result is scored: official site +5, PDF +2, right document type +4, right quarter +4, news/broker -10.
3. Only candidates scoring 9+ are downloaded. The file is opened and must contain the company name and the quarter.
4. News and broker pages are kept as Tier 4 leads, never as evidence.
5. One PDF can cover two needs (Axis files one PDF with press release + investor presentation).

## Known gaps (not hidden)
- Live search and live downloads were NOT tested from the build sandbox (no internet). Test on your PC first.
- Annual report, rating rationale, exchange filings and Pillar 3 did not appear in the real Axis searches. The `site:` follow-up query is built but untested live.
- A short exchange cover letter can point to the real document by link; link-following is not built yet.
- Peers are not chosen automatically yet.
- Websites whose name contains the company name are treated as official (a broker site with the same name could slip in; the open-and-verify step and the Tier rules limit the damage).
