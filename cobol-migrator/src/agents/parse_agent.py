import re
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from src.state import MigrationState
from src.llm import chat


_COBOL_EXTENSIONS = {".cbl", ".cob", ".cobol"}


def _to_raw_url(url: str) -> str:
    """Convert a github.com blob URL to raw.githubusercontent.com."""
    return (
        url.replace("github.com", "raw.githubusercontent.com")
           .replace("/blob/", "/")
    )


def _fetch_source(url: str) -> str:
    if not url.startswith("https://") or "github.com" not in url:
        raise ValueError(f"Invalid URL: must be an https github.com link, got: {url}")
    raw_url = _to_raw_url(url)
    resp = httpx.get(raw_url, timeout=10, follow_redirects=True)
    resp.raise_for_status()
    return resp.text


def _extract_variables(source: str) -> list[str]:
    # Parse line-by-line to avoid DOTALL greedy-lookahead issues
    lines = source.splitlines()
    in_ws = False
    ws_lines: list[str] = []
    for line in lines:
        if re.match(r"\s*WORKING-STORAGE\s+SECTION", line, re.IGNORECASE):
            in_ws = True
            continue
        if in_ws:
            if re.match(r"\s*\w[\w-]*\s+DIVISION", line, re.IGNORECASE):
                break
            ws_lines.append(line)
    ws_text = "\n".join(ws_lines)
    return re.findall(r"^\s*\d+\s+([\w-]+)\s+PIC", ws_text, re.MULTILINE | re.IGNORECASE)


def _extract_copy_refs(source: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\bCOPY\s+([\w-]+)", source, re.IGNORECASE)))


def _extract_call_refs(source: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"\bCALL\s+['\"]?([\w-]+)['\"]?", source, re.IGNORECASE)))


# COBOL reserved words that look like paragraph names but are statements
_COBOL_KEYWORDS = {
    "STOP", "GOBACK", "EXIT", "CONTINUE", "NEXT", "END", "ELSE",
    "MOVE", "COMPUTE", "ADD", "SUBTRACT", "MULTIPLY", "DIVIDE",
    "DISPLAY", "ACCEPT", "PERFORM", "CALL", "IF", "EVALUATE",
    "READ", "WRITE", "OPEN", "CLOSE", "RETURN",
}


def _extract_paragraphs(
    source: str,
    variables: list[str],
    copy_refs: list[str],
    call_refs: list[str],
) -> list[dict]:
    proc_match = re.search(r"PROCEDURE DIVISION.*?\.(.*)", source, re.DOTALL | re.IGNORECASE)
    proc_body = proc_match.group(1) if proc_match else source

    # Paragraph names: optional leading whitespace, bare identifier, then a period
    # Handles both standard (col 8) and indented COBOL source
    parts = re.split(r"\n[ \t]*([\w][\w-]*)\s*\.\s*(?=\n)", proc_body)

    paragraphs: list[dict] = []
    if len(parts) >= 3:
        for i in range(1, len(parts), 2):
            name = parts[i].strip().upper()
            body = parts[i + 1].strip() if i + 1 < len(parts) else ""
            if body and name not in _COBOL_KEYWORDS:
                paragraphs.append({
                    "name": name,
                    "body": body,
                    "summary": "",
                    "variables": variables,
                    "copy_refs": copy_refs,
                    "call_refs": call_refs,
                })

    if not paragraphs:
        paragraphs.append({
            "name": "MAIN",
            "body": proc_body.strip(),
            "summary": "",
            "variables": variables,
            "copy_refs": copy_refs,
            "call_refs": call_refs,
        })

    return paragraphs


def _summarize(name: str, body: str) -> str:
    return chat(
        messages=[{"role": "user", "content": f"In one sentence, describe what this COBOL paragraph '{name}' does:\n\n{body}"}],
        max_tokens=150,
    ).strip()


def parse_agent(state: MigrationState) -> MigrationState:
    try:
        source = state["source_code"]
        if state.get("source_url"):
            source = _fetch_source(state["source_url"])

        variables = _extract_variables(source)
        copy_refs = _extract_copy_refs(source)
        call_refs = _extract_call_refs(source)
        paragraphs = _extract_paragraphs(source, variables, copy_refs, call_refs)

        # Summarise all paragraphs in parallel to avoid sequential LLM latency
        with ThreadPoolExecutor(max_workers=min(len(paragraphs), 4)) as pool:
            futures = {pool.submit(_summarize, p["name"], p["body"]): i for i, p in enumerate(paragraphs)}
            for fut in as_completed(futures):
                paragraphs[futures[fut]]["summary"] = fut.result()

        return {**state, "source_code": source, "paragraphs": paragraphs, "status": "parsing"}

    except Exception as e:
        return {**state, "status": "failed", "error_log": state["error_log"] + [f"ParseAgent: {e}"]}
