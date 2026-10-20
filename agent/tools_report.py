import json

from agent import DATA, OUT, build_report


def write_report(fmt="docx", narrative=None):
    """Save the model's narrative (if given), then build the report files from the saved state."""
    if narrative:
        (DATA / "narrative.json").write_text(json.dumps(narrative, indent=2, ensure_ascii=False), encoding="utf-8")
    OUT.mkdir(exist_ok=True)
    from agent import tools_state                  # always refresh the code-computed parts first
    try:
        tools_state.get_relationships()
    except Exception:
        pass
    if (DATA / "leads.json").exists() and json.loads((DATA / "leads.json").read_text(encoding="utf-8")):
        tools_state.score_leads()
    out = {}
    if fmt in ("docx", "both"):
        try:
            out["docx"] = str(build_report.build_docx(OUT / "Signal_Hunter_Report.docx"))
        except Exception as e:
            out["docx_error"] = f"{type(e).__name__}: {e}"
    if fmt in ("json", "both"):
        try:
            out["json"] = str(build_report.build_json(OUT / "Signal_Hunter_Report.json"))
        except Exception as e:
            out["json_error"] = f"{type(e).__name__}: {e}"
    return out
