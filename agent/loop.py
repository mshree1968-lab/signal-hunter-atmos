"""Signal Hunter: the agent loop (Anthropic SDK, native tool use).
Claude decides what to look at; every number, check and score is computed by the Python tools.
Run:  python agent/loop.py "Bajaj Finance" express
"""
import json, os, sys, time, traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

import logging
logging.getLogger("pypdf").setLevel(logging.ERROR)     # hide harmless PDF-format warnings on screen

import anthropic

from agent import DATA, OUT
from agent.llm import COST, MODEL, client

MAX_TOOL_CALLS = int(os.environ.get("MAX_TOOL_CALLS", "25"))
MAX_TOOL_CALLS_FULL = int(os.environ.get("MAX_TOOL_CALLS_FULL", "60"))
MAX_COST_USD = float(os.environ.get("MAX_COST_USD", "1.50"))
WEB_SEARCH = {"type": "web_search_20260209", "name": "web_search", "max_uses": 2}


def _obj(props, required):
    return {"type": "object", "properties": props, "required": required}


FACT = _obj({"metric": {"type": "string"}, "value": {"type": "number"}, "unit": {"type": "string"},
             "period": {"type": "string"}, "scope": {"type": "string", "enum": ["standalone", "consolidated"]},
             "doc": {"type": "string", "description": "document id, e.g. D01"},
             "page": {"type": "string"}, "excerpt": {"type": "string", "description": "exact text copied from the page, max 20 words"},
             "definition_as_reported": {"type": "string"}},
            ["metric", "value", "unit", "period", "scope", "doc", "page", "excerpt"])
BOOL5 = {"type": "array", "items": {"type": "boolean"}, "minItems": 5, "maxItems": 5}

TOOLS = [
    {"name": "find_documents",
     "description": "Search the web for the company's documents (presentation, results, rating rationale...), "
                    "download them, open them and verify company and quarter. Returns document ids. Call once at P1.",
     "input_schema": _obj({"company": {"type": "string"}, "symbol": {"type": "string"},
                           "archetype": {"type": "string", "enum": ["bank", "nbfc", "hfc", "life", "general", "exchange",
                                                                    "amc", "holding", "government_lender", "card_specialty"]}},
                          ["company", "symbol", "archetype"])},
    {"name": "fetch_url",
     "description": "Download one URL. A PDF is saved and gets a document id; a web page returns trimmed text and PDF links.",
     "input_schema": _obj({"url": {"type": "string"}}, ["url"])},
    {"name": "find_in_pdf",
     "description": "List the pages of a document that mention any keyword, with a short snippet each.",
     "input_schema": _obj({"doc": {"type": "string"}, "keywords": {"type": "array", "items": {"type": "string"}}},
                          ["doc", "keywords"])},
    {"name": "read_pdf",
     "description": "Read page text from a document. pages like '7' or '7-9' (max 4 pages per call).",
     "input_schema": _obj({"doc": {"type": "string"}, "pages": {"type": "string"}}, ["doc", "pages"])},
    {"name": "save_facts",
     "description": "Save facts to the provenance store. Code re-opens the page and verifies excerpt and number. Returns fact ids.",
     "input_schema": _obj({"facts": {"type": "array", "items": FACT}}, ["facts"])},
    {"name": "calculate",
     "description": "Run a fixed formula in code. Inputs may be numbers or fact ids. Names: growth_pct(closing,opening), "
                    "stage3_pct(stage3,gross_loans), stage2_pct(stage2,gross_loans), write_off_rate(writeoffs,opening_stage3), "
                    "adjusted_gnpa(gnpa,writeoffs,loans), provision_coverage(stage3_provisions,stage3_gross), "
                    "credit_cost(impairment,average_loans[,annualise]), cost_of_funds(interest_expense,average_borrowings[,annualise]), "
                    "share_pct(part,total), ape, vnb_margin, solvency_ratio, loss_ratio, combined_ratio, transaction_yield, "
                    "core_income, amc_yield, net_flows, qaaum_share.",
     "input_schema": _obj({"name": {"type": "string"}, "inputs": {"type": "object"}, "label": {"type": "string"}},
                          ["name", "inputs"])},
    {"name": "get_relationships",
     "description": "Evaluate R1-R17 in code against the verified facts. Returns CLEAN / FLAGGED / NOT-TESTABLE per edge.",
     "input_schema": _obj({}, [])},
    {"name": "save_lead",
     "description": "Register one lead. tests: 5 yes/no answers for each of discovery, evidence, cross_source, temporal, "
                    "falsifiability, robustness (order as in Section 12.0). Code overwrites machine-checked answers.",
     "input_schema": _obj({
         "id": {"type": "string"}, "name": {"type": "string"},
         "fact_ids": {"type": "array", "items": {"type": "string"}},
         "calc_ids": {"type": "array", "items": {"type": "string"}},
         "tests": _obj({d: BOOL5 for d in ["discovery", "evidence", "cross_source", "temporal", "falsifiability", "robustness"]},
                       ["discovery", "evidence", "cross_source", "temporal", "falsifiability", "robustness"]),
         "counter_categories_searched": {"type": "integer"}, "falsification_criteria_met": {"type": "integer"},
         "confounders_checked": {"type": "boolean"}, "counter_strength": {"type": "string", "enum": ["Strong", "Moderate", "Weak"]},
         "counter_resolved": {"type": "boolean"}, "unresolved_strong_counter": {"type": "boolean"},
         "unresolved_conflict": {"type": "boolean"}, "is_company_headline": {"type": "boolean"}},
         ["id", "name", "fact_ids", "calc_ids", "tests", "counter_categories_searched", "falsification_criteria_met",
          "confounders_checked", "counter_strength", "is_company_headline"])},
    {"name": "score_leads",
     "description": "Run the gates and scoring code on all registered leads. Returns the verdict.",
     "input_schema": _obj({}, [])},
    {"name": "write_report",
     "description": "Write outputs/Signal_Hunter_Report.docx (and .json) from the saved state plus your narrative. "
                    "narrative keys: discovery, why_it_matters (list), evidence (list), timeline (list), numbers_calc_ids (list), "
                    "counterargument, falsification, evidence_strength, terms (list), limitations (list), missing_sources (list), "
                    "coverage_grade (Full/Partial/Limited), peers_checked, verification_notes (list).",
     "input_schema": _obj({"format": {"type": "string", "enum": ["docx", "json", "both"]},
                           "narrative": {"type": "object"}}, ["format", "narrative"])},
    WEB_SEARCH,
]


def run_tool(name, args):
    from agent import tools_web, tools_parse, tools_calc, tools_state, tools_report
    if name == "find_documents":    return tools_web.find_documents(args["company"], args.get("symbol", ""), args["archetype"], RUN["mode"])
    if name == "fetch_url":         return tools_web.fetch_url(args["url"])
    if name == "find_in_pdf":       return tools_parse.find_in_pdf(args["doc"], args["keywords"])
    if name == "read_pdf":          return tools_parse.read_pdf(args["doc"], args.get("pages", "1-3"))
    if name == "save_facts":        return tools_state.save_facts(args["facts"])
    if name == "calculate":         return tools_calc.calculate(args["name"], args["inputs"], args.get("label", ""))
    if name == "get_relationships": return tools_state.get_relationships()
    if name == "save_lead":         return tools_state.save_lead(args)
    if name == "score_leads":       return tools_state.score_leads()
    if name == "write_report":
        gap = _too_early()
        if gap:
            return gap
        RUN["report_written"] = True
        _save_run()
        return tools_report.write_report(args.get("format", "both"), args.get("narrative"))
    return {"error": f"unknown tool: {name}"}


RUN = {}
KEY_METRICS = ["aum", "gross_loans", "stage3_amount", "stage2_amount", "writeoffs", "ppop", "pbt",
               "cost_of_funds", "nim"]


def _too_early():
    """Code-level stop rule: the first early write_report is refused if the data is too thin to test
    the relationships. It lists exactly what is missing. Refused at most once per run."""
    if RUN.get("early_checked") or RUN.get("calls", 0) >= 0.6 * RUN["tool_budget"]:
        return None
    RUN["early_checked"] = True
    from agent import relationships
    from agent.tools_state import FACTS, _load
    facts = [f for f in _load(FACTS) if f.get("verified")]
    testable = [e for e in relationships.evaluate(facts)["edges"] if e["status"] != "NOT-TESTABLE"] if facts else []
    if len(testable) >= 3:
        return None
    periods = {}
    for f in facts:
        periods.setdefault(f["metric"].lower(), set()).add(relationships.to_label(f.get("period", "")))
    thin = [mt for mt in KEY_METRICS if len(periods.get(mt, ())) < 2]
    has_seg = any(mt.startswith("segment_aum:") for mt in periods)
    return {"error": "Too early to write the report: only %d relationship edges are testable." % len(testable),
            "missing_two_periods_for": thin, "segment_table_saved": has_seg,
            "do_next": "Save these metrics for the latest quarter and the same quarter last year (period 'Q1 FY27' style), "
                       "plus the segment table, call get_relationships, register leads, score_leads, then write_report."}


def _save_run():
    RUN["cost"] = COST.summary()
    (DATA / "run.json").write_text(json.dumps(RUN, indent=2, ensure_ascii=False), encoding="utf-8")


def say(msg):
    print(msg, flush=True)


def _brief(name, args, result):
    """One readable line per tool call, for the screen."""
    r = result if isinstance(result, dict) else {}
    if name == "find_documents":
        docs = r.get("documents", [])
        return (f"found {len(docs)} document(s) via {r.get('route')}; anchor quarter {r.get('anchor_quarter')}; "
                f"missing: {', '.join(r.get('missing', [])) or 'none'}")
    if name == "save_facts" and isinstance(result, list):
        ok = sum(x["verified"] for x in result)
        return f"saved {len(result)} fact(s); {ok} verified on the page by code, {len(result) - ok} not verified"
    if name == "calculate":
        return f"{r.get('id')} {r.get('label') or r.get('name')} = {r.get('value')}  ({r.get('formula')})"
    if name == "get_relationships":
        return f"relationship map: {r.get('summary')}"
    if name == "score_leads":
        return f"verdict: {r.get('verdict')}"
    if name == "read_pdf":
        return f"read {args.get('doc')} pages {args.get('pages')}"
    if name == "find_in_pdf":
        return f"{len(r.get('hits', []))} page hit(s) in {args.get('doc')} for {args.get('keywords')}"
    if "error" in r:
        return f"ERROR {r['error']}"
    return json.dumps(result, ensure_ascii=False)[:160]


def agent_loop(company, mode="express", max_turns=40):
    from agent import tools_state, tools_report
    OUT.mkdir(exist_ok=True)
    rules = ROOT / ".clinerules"
    if not rules.exists():
        return {"error": ".clinerules not found at repo root"}
    system = rules.read_text(encoding="utf-8")
    tools_state.reset()
    budget = MAX_TOOL_CALLS_FULL if mode == "full" else MAX_TOOL_CALLS
    RUN.clear()
    RUN.update(company=company, mode=mode, as_of=time.strftime("%Y-%m-%d"), model=MODEL,
               tool_budget=budget, cost_cap_usd=MAX_COST_USD, report_written=False)
    _save_run()

    user_msg = (f"company_name: {company}\nas_of_date: {RUN['as_of']}\nmode: {mode}\npeers: auto\n"
                f"output_format: report + JSON\ntool_call_budget: {budget}\n\n"
                "Begin at P0. Follow Section 17. Use tools; keep any text between tool calls to one short line. "
                "If no lead passes all gates, write_report must say 'No Strong Finding': that is a valid outcome.")
    messages = [{"role": "user", "content": user_msg}]
    calls, warned, start = 0, False, time.time()
    say(f"\n=== Signal Hunter | {company} | {mode} mode | model {MODEL} | budget {budget} tool calls, US$ {MAX_COST_USD} ===")

    for turn in range(max_turns):
        try:
            resp = client().messages.create(
                model=MODEL, max_tokens=16000, system=system, tools=TOOLS, messages=messages,
                cache_control={"type": "ephemeral"}, output_config={"effort": "medium"})
        except anthropic.APIStatusError as e:
            say(f"API error {e.status_code}: {e.message}")
            RUN["stopped_early"] = f"API error {e.status_code}"
            break
        except anthropic.APIConnectionError:
            say("Network error talking to the Anthropic API.")
            RUN["stopped_early"] = "network error"
            break
        COST.add(resp.usage)
        messages.append({"role": "assistant", "content": resp.content})
        for b in resp.content:
            if b.type == "text" and b.text.strip():
                say(f"  Claude: {b.text.strip()[:200]}")
            if b.type == "server_tool_use":
                say(f"  [web] Claude web search: {json.dumps(b.input, ensure_ascii=False)[:120]}")

        if resp.stop_reason == "pause_turn":
            continue
        if resp.stop_reason == "refusal":
            RUN["stopped_early"] = "model refusal"
            break
        if resp.stop_reason != "tool_use":
            if RUN["report_written"]:
                break
            messages.append({"role": "user", "content": "The report is not written yet. Call score_leads if needed, then write_report now."})
            continue

        results = []
        for b in resp.content:
            if b.type != "tool_use":
                continue
            calls += 1
            RUN["calls"] = calls
            t0 = time.time()
            try:
                out = run_tool(b.name, b.input)
                err = isinstance(out, dict) and "error" in out
            except Exception as e:
                out = {"error": f"{type(e).__name__}: {e}", "trace": traceback.format_exc().splitlines()[-3:]}
                err = True
            say(f"  [{calls:02d}] {b.name}: {_brief(b.name, b.input, out)}  ({time.time() - t0:.0f}s)")
            content = json.dumps(out, ensure_ascii=False, default=str)[:12000]
            results.append({"type": "tool_result", "tool_use_id": b.id, "content": content, "is_error": err})

        spent = COST.usd()
        if RUN["report_written"] and not any(b.type == "tool_use" and b.name != "write_report" for b in resp.content):
            messages.append({"role": "user", "content": results})
            break
        if calls >= budget or spent >= MAX_COST_USD:
            RUN["stopped_early"] = f"budget reached ({calls} tool calls, US$ {spent:.2f})"
            messages.append({"role": "user", "content": results})
            break
        if not warned and (calls >= 0.75 * budget or spent >= 0.75 * MAX_COST_USD):
            warned = True
            results.append({"type": "text", "text": "Budget nearly used. Stop collecting now: save_lead for your leads, "
                                                    "score_leads, then write_report."})
            say("  >> budget 75% used: asking the agent to wrap up")
        messages.append({"role": "user", "content": results})

    if not RUN["report_written"]:              # guarantee a report, built only from saved state
        say("  >> writing the report from saved state (the agent did not finish in budget)")
        tools_state.score_leads() if (DATA / "leads.json").exists() and json.loads((DATA / "leads.json").read_text()) else None
        try:
            tools_state.get_relationships()
        except Exception:
            pass
        narrative = {"discovery": "No Strong Finding: the run stopped before an investigated finding was completed.",
                     "limitations": [f"Run stopped early: {RUN.get('stopped_early', 'turn limit')}"],
                     "coverage_grade": "Limited"}
        nf = DATA / "narrative.json"
        if not nf.exists():
            nf.write_text(json.dumps(narrative, indent=2), encoding="utf-8")
        RUN["report_written"] = True
        _save_run()
        tools_report.write_report("both")

    _save_run()
    import re, shutil                          # keep a per-company copy so runs do not overwrite each other
    slug = re.sub(r"[^A-Za-z0-9]+", "_", company).strip("_")
    for ext in ("docx", "json"):
        src = OUT / f"Signal_Hunter_Report.{ext}"
        if src.exists():
            shutil.copy(src, OUT / f"Signal_Hunter_Report_{slug}.{ext}")
    minutes = (time.time() - start) / 60
    c = COST.summary()
    say(f"\n=== Done in {minutes:.1f} min | {calls} tool calls | {c['api_calls']} API calls | "
        f"{c['web_searches']} Claude web searches | estimated cost US$ {c['estimated_usd']:.2f} ===")
    say(f"Report: {OUT / 'Signal_Hunter_Report.docx'}")
    return {"tool_calls": calls, "minutes": round(minutes, 1), **c}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit('usage: python agent/loop.py "Company Name" [express|full]')
    agent_loop(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "express")
