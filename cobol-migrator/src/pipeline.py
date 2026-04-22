import io
import os
import re
import tempfile
import uuid
import zipfile
from pathlib import Path

import httpx
from dotenv import load_dotenv
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver

from src.state import MigrationState, RepoMigrationResult
from src.agents.parse_agent import parse_agent
from src.agents.translate_agent import translate_agent
from src.agents.validate_agent import validate_agent
from src.agents.reflect_agent import reflect_agent
from src.agents.document_agent import document_agent

load_dotenv()

_COBOL_SUFFIXES = {".cbl", ".cob", ".cobol"}

# Shared in-memory checkpointer — persists state per thread_id across node transitions.
# Each migration job runs under its own thread_id (= job_id from the API).
_checkpointer = MemorySaver()


# ── Routing ───────────────────────────────────────────────────────────────────

def _should_retry(state: MigrationState) -> str:
    """
    Route after validate:
      "reflect"  → there are concrete errors to reason about (→ reflect → translate)
      "document" → all clear, or we've hit max iterations
    """
    if state["iteration_count"] >= state["max_iterations"]:
        return "document"

    results = state["test_results"]
    has_failures  = results.get("failed", 0) > 0
    has_lint      = len(state["lint_results"]) > 0
    # Any test error: import failure, collection error, timeout — total=0 with errors present
    has_test_error = results.get("total", 0) == 0 and len(results.get("errors", [])) > 0

    if has_failures or has_lint or has_test_error:
        return "reflect"
    return "document"


# ── Graph ─────────────────────────────────────────────────────────────────────

def _build_pipeline():
    graph = StateGraph(MigrationState)

    graph.add_node("parse",     parse_agent)
    graph.add_node("translate", translate_agent)
    graph.add_node("validate",  validate_agent)
    graph.add_node("reflect",   reflect_agent)
    graph.add_node("document",  document_agent)

    graph.add_edge(START,       "parse")
    graph.add_edge("parse",     "translate")
    graph.add_edge("translate", "validate")
    graph.add_conditional_edges(
        "validate", _should_retry,
        {"reflect": "reflect", "document": "document"},
    )
    graph.add_edge("reflect",   "translate")
    graph.add_edge("document",  END)

    return graph.compile(checkpointer=_checkpointer)


_pipeline = _build_pipeline()


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_initial_state(
    source_code: str,
    source_url: str | None = None,
    file_path: str | None = None,
) -> MigrationState:
    return {
        "source_code": source_code,
        "source_url": source_url,
        "file_path": file_path,
        "paragraphs": [],
        "translated_code": "",
        "test_code": "",
        "test_results": {"passed": 0, "failed": 0, "errors": [], "total": 0},
        "lint_results": [],
        "iteration_count": 0,
        "max_iterations": int(os.getenv("MAX_ITERATIONS", "3")),
        "error_log": [],
        "documentation": "",
        "confidence_score": 0.0,
        "status": "starting",
        "reflection": "",
        "fix_plan": "",
    }


def _parse_github_repo_url(url: str) -> tuple[str, str]:
    match = re.match(r"https?://github\.com/([^/]+)/([^/]+?)(?:\.git|/.*)?$", url)
    if not match:
        raise ValueError(f"Cannot parse GitHub repo URL: {url}")
    return match.group(1), match.group(2)


def _download_repo_zip(owner: str, repo: str) -> bytes:
    archive_url = f"https://github.com/{owner}/{repo}/archive/HEAD.zip"
    resp = httpx.get(archive_url, timeout=60, follow_redirects=True)
    resp.raise_for_status()
    return resp.content


# ── Public API ────────────────────────────────────────────────────────────────

def run_migration(
    source_code: str,
    source_url: str | None = None,
    file_path: str | None = None,
    thread_id: str | None = None,
) -> MigrationState:
    """
    Migrate a single COBOL file to Python 3.

    Each call runs under a unique thread_id so LangGraph checkpoints every
    node's state in _checkpointer.  Pass the same thread_id to inspect or
    resume a prior run via get_checkpointed_state().
    """
    tid = thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": tid}}
    return _pipeline.invoke(_make_initial_state(source_code, source_url, file_path), config=config)


def get_checkpointed_state(thread_id: str) -> dict | None:
    """Return the latest LangGraph checkpoint for a given thread_id, or None."""
    try:
        snapshot = _pipeline.get_state({"configurable": {"thread_id": thread_id}})
        return dict(snapshot.values) if snapshot else None
    except Exception:
        return None


def run_repo_migration(repo_url: str) -> RepoMigrationResult:
    """Migrate every COBOL file in a GitHub repository to Python 3."""
    owner, repo = _parse_github_repo_url(repo_url)
    zip_bytes = _download_repo_zip(owner, repo)

    results: list[MigrationState] = []
    all_file_stems: set[str] = set()

    with tempfile.TemporaryDirectory() as tmpdir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            zf.extractall(tmpdir)

        root = Path(tmpdir)
        cobol_files = [p for p in root.rglob("*") if p.suffix.lower() in _COBOL_SUFFIXES]
        all_file_stems = {p.stem.upper() for p in cobol_files}

        for cobol_path in cobol_files:
            rel_path = str(cobol_path.relative_to(root))
            source_code = cobol_path.read_text(errors="replace")
            result = run_migration(source_code, file_path=rel_path)
            results.append(result)

    all_copy_refs: set[str] = set()
    all_call_refs: set[str] = set()
    for r in results:
        for p in r.get("paragraphs", []):
            all_copy_refs.update(c.upper() for c in p.get("copy_refs", []))
            all_call_refs.update(c.upper() for c in p.get("call_refs", []))

    unresolved_copies = sorted(all_copy_refs - all_file_stems)
    unresolved_calls  = sorted(all_call_refs - all_file_stems)

    completed = [r for r in results if r["status"] == "done"]
    failed    = [r for r in results if r["status"] == "failed"]
    avg_confidence = (
        sum(r["confidence_score"] for r in completed) / len(completed)
        if completed else 0.0
    )

    if not results:       agg_status = "failed"
    elif not failed:      agg_status = "done"
    elif completed:       agg_status = "partial"
    else:                 agg_status = "failed"

    return {
        "repo_url": repo_url,
        "total_files": len(results),
        "completed_files": len(completed),
        "failed_files": len(failed),
        "files": results,
        "unresolved_copies": unresolved_copies,
        "unresolved_calls": unresolved_calls,
        "average_confidence": round(avg_confidence, 2),
        "status": agg_status,
    }
