from src.state import MigrationState
from src.llm import chat


def _compute_confidence(state: MigrationState) -> float:
    results = state["test_results"]
    total = results.get("total", 0)
    passed = results.get("passed", 0)

    test_score = (passed / total) if total > 0 else 0.0
    lint_score = 1.0 if len(state["lint_results"]) == 0 else 0.0

    return round(test_score * 0.7 + lint_score * 0.3, 2)


def _build_mapping_table(state: MigrationState) -> str:
    rows = ["| COBOL Paragraph | Python Function | Purpose |", "|---|---|---|"]
    for p in state["paragraphs"]:
        py_name = p["name"].lower().replace("-", "_")
        rows.append(f"| {p['name']} | {py_name}() | {p['summary']} |")
    return "\n".join(rows)


def _generate_report(state: MigrationState, mapping_table: str, confidence: float) -> str:
    all_copy = list({r for p in state["paragraphs"] for r in p.get("copy_refs", [])})
    all_call = list({r for p in state["paragraphs"] for r in p.get("call_refs", [])})

    unresolved_section = ""
    if all_copy or all_call:
        unresolved_section = (
            f"\nUnresolved references that need manual attention:\n"
            + (f"  COPY: {', '.join(sorted(all_copy))}\n" if all_copy else "")
            + (f"  CALL: {', '.join(sorted(all_call))}\n" if all_call else "")
        )

    tests = state["test_results"]
    prompt = (
        "Write a concise migration report in Markdown for a COBOL → Python 3 migration.\n"
        "Include: semantic changes (COMPUTE→arithmetic, MOVE→assignment, DISPLAY→print, etc.), "
        "any known limitations, and recommended next steps.\n"
        "Keep it under 300 words. Output only the Markdown, no code fences.\n\n"
        f"Paragraph mapping:\n{mapping_table}\n\n"
        f"Test results: {tests.get('passed',0)}/{tests.get('total',0)} passed, "
        f"{len(state['lint_results'])} lint warnings.\n"
        f"Confidence score: {confidence * 100:.0f}%"
        f"{unresolved_section}"
    )

    return chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    ).strip()


def document_agent(state: MigrationState) -> MigrationState:
    try:
        confidence = _compute_confidence(state)
        mapping_table = _build_mapping_table(state)
        report_body = _generate_report(state, mapping_table, confidence)

        tests = state["test_results"]
        header = (
            f"# Migration Report\n\n"
            f"**Confidence Score:** {confidence * 100:.0f}%  \n"
            f"**Tests:** {tests.get('passed', 0)}/{tests.get('total', 0)} passed  \n"
            f"**Lint warnings:** {len(state['lint_results'])}  \n"
            f"**Iterations:** {state['iteration_count']}\n\n"
            f"## Paragraph → Function Mapping\n\n{mapping_table}\n\n"
            f"## Summary\n\n"
        )

        documentation = header + report_body

        return {
            **state,
            "status": "done",
            "confidence_score": confidence,
            "documentation": documentation,
        }

    except Exception as e:
        return {
            **state,
            "status": "done",
            "confidence_score": _compute_confidence(state),
            "documentation": f"# Migration Report\n\nReport generation failed: {e}",
            "error_log": state["error_log"] + [f"DocumentAgent: {e}"],
        }
