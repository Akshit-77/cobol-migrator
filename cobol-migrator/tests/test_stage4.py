"""
Stage 4 tests — FastAPI backend.

Unit tests use TestClient and mock the pipeline so no LLM calls are made.
Integration tests (marked) run real pipeline calls and require an API key.

Run with: uv run pytest tests/test_stage4.py -v
"""
import os
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from src.api import app, _jobs

client = TestClient(app)


def _make_done_state(**overrides) -> dict:
    base = {
        "source_code": "x = 1",
        "source_url": None,
        "file_path": None,
        "paragraphs": [{"name": "MAIN", "body": "", "summary": "does stuff", "variables": [], "copy_refs": [], "call_refs": []}],
        "translated_code": "def main():\n    pass",
        "test_code": "def test_main(): pass",
        "test_results": {"passed": 1, "failed": 0, "errors": [], "total": 1},
        "lint_results": [],
        "iteration_count": 1,
        "max_iterations": 3,
        "error_log": [],
        "documentation": "# Migration Report\n\n**Confidence Score:** 100%",
        "confidence_score": 1.0,
        "status": "done",
    }
    base.update(overrides)
    return base


# ── Health endpoint ────────────────────────────────────────────────────────────

class TestHealth:
    def test_returns_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_returns_job_count(self):
        r = client.get("/api/health")
        assert "jobs" in r.json()


# ── POST /api/migrate ─────────────────────────────────────────────────────────

class TestPostMigrate:
    def test_requires_at_least_one_input(self):
        r = client.post("/api/migrate", json={})
        assert r.status_code == 422

    def test_source_code_accepted(self):
        with patch("src.api._run_job"):
            r = client.post("/api/migrate", json={"source_code": "IDENTIFICATION DIVISION."})
        assert r.status_code == 202
        body = r.json()
        assert "job_id" in body
        assert body["status"] == "queued"

    def test_source_url_accepted(self):
        with patch("src.api._run_job"):
            r = client.post("/api/migrate", json={"source_url": "https://github.com/owner/repo/blob/main/file.cbl"})
        assert r.status_code == 202

    def test_repo_url_accepted(self):
        with patch("src.api._run_job"):
            r = client.post("/api/migrate", json={"repo_url": "https://github.com/owner/repo"})
        assert r.status_code == 202

    def test_returns_unique_job_ids(self):
        with patch("src.api._run_job"):
            r1 = client.post("/api/migrate", json={"source_code": "A"})
            r2 = client.post("/api/migrate", json={"source_code": "B"})
        assert r1.json()["job_id"] != r2.json()["job_id"]


# ── GET /api/status/{job_id} ──────────────────────────────────────────────────

class TestGetStatus:
    def test_unknown_job_returns_404(self):
        r = client.get(f"/api/status/{uuid.uuid4()}")
        assert r.status_code == 404

    def test_queued_job_returns_queued(self):
        with patch("src.api._run_job"):
            job_id = client.post("/api/migrate", json={"source_code": "X"}).json()["job_id"]
        r = client.get(f"/api/status/{job_id}")
        assert r.status_code == 200
        assert r.json()["status"] == "queued"

    def test_done_job_has_result(self):
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": "done", "result": _make_done_state(), "error": None}
        r = client.get(f"/api/status/{job_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "done"
        assert body["result"] is not None

    def test_failed_job_has_error(self):
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": "failed", "result": None, "error": "Something broke"}
        r = client.get(f"/api/status/{job_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "failed"
        assert "Something broke" in body["error"]

    def test_result_contains_confidence_score(self):
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": "done", "result": _make_done_state(confidence_score=0.85), "error": None}
        r = client.get(f"/api/status/{job_id}")
        assert r.json()["result"]["confidence_score"] == 0.85

    def test_result_contains_documentation(self):
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": "done", "result": _make_done_state(), "error": None}
        r = client.get(f"/api/status/{job_id}")
        assert "Migration Report" in r.json()["result"]["documentation"]

    def test_result_contains_translated_code(self):
        job_id = str(uuid.uuid4())
        _jobs[job_id] = {"status": "done", "result": _make_done_state(), "error": None}
        r = client.get(f"/api/status/{job_id}")
        assert r.json()["result"]["translated_code"]


# ── Integration tests (real LLM) ──────────────────────────────────────────────

HAS_API_KEY = any(
    os.getenv(k)
    for k in ["ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GROQ_API_KEY", "GROK_API_KEY", "GEMINI_API_KEY"]
)

_SAMPLE_COBOL = """\
IDENTIFICATION DIVISION.
PROGRAM-ID. COMPUTE-INTEREST.

WORKING-STORAGE SECTION.
01 WS-PRINCIPAL PIC 9(9)V99.
01 WS-RATE      PIC 9(3)V99.
01 WS-YEARS     PIC 9(3).
01 WS-INTEREST  PIC 9(9)V99.

PROCEDURE DIVISION.
COMPUTE-INTEREST.
    COMPUTE WS-INTEREST = WS-PRINCIPAL * WS-RATE / 100 * WS-YEARS.
    IF WS-INTEREST > 10000
        MOVE 10000 TO WS-INTEREST.
    DISPLAY WS-INTEREST.
    STOP RUN.
"""


@pytest.mark.skipif(not HAS_API_KEY, reason="No LLM API key found in environment")
class TestMigrateIntegration:
    def test_full_flow_source_code(self):
        """Submit a job, poll until done, verify result shape."""
        import time

        r = client.post("/api/migrate", json={"source_code": _SAMPLE_COBOL})
        assert r.status_code == 202
        job_id = r.json()["job_id"]

        # Poll up to 3 minutes
        for _ in range(36):
            time.sleep(5)
            sr = client.get(f"/api/status/{job_id}")
            assert sr.status_code == 200
            if sr.json()["status"] in ("done", "failed"):
                break

        result = sr.json()
        assert result["status"] == "done", f"Pipeline failed: {result}"
        assert result["result"]["translated_code"]
        assert result["result"]["confidence_score"] >= 0.0
        assert "Migration Report" in result["result"]["documentation"]
