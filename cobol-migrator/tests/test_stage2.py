"""
Stage 2 tests — Parse Agent and Translate Agent.

These tests require a valid LLM API key (set LLM_PROVIDER + matching key in .env).
They make real LLM calls and are therefore integration tests, not unit tests.
Run with: uv run pytest tests/test_stage2.py -v
"""
import os
import pytest
from pathlib import Path

from src.pipeline import run_migration, _parse_github_repo_url
from src.agents.parse_agent import (
    _extract_variables,
    _extract_copy_refs,
    _extract_call_refs,
    _extract_paragraphs,
    _to_raw_url,
)

SAMPLE_COBOL = Path(__file__).parent / "sample.cbl"


# ── Pure parsing helpers (no LLM, no network) ─────────────────────────────────

class TestExtractVariables:
    def test_extracts_ws_variables(self):
        source = (
            "WORKING-STORAGE SECTION.\n"
            "01 WS-PRINCIPAL PIC 9(9)V99.\n"
            "01 WS-RATE PIC 9(3)V99.\n"
            "PROCEDURE DIVISION.\n"
        )
        vars_ = _extract_variables(source)
        assert "WS-PRINCIPAL" in vars_
        assert "WS-RATE" in vars_

    def test_empty_when_no_working_storage(self):
        assert _extract_variables("PROCEDURE DIVISION.\nMAIN.\n    STOP RUN.") == []


class TestExtractCopyRefs:
    def test_finds_copy_statements(self):
        source = "COPY CUSTDATA.\nCOPY ACCTDATA."
        refs = _extract_copy_refs(source)
        assert "CUSTDATA" in refs
        assert "ACCTDATA" in refs

    def test_deduplicates(self):
        source = "COPY CUSTDATA.\nCOPY CUSTDATA."
        assert _extract_copy_refs(source).count("CUSTDATA") == 1

    def test_empty_when_none(self):
        assert _extract_copy_refs("DISPLAY 'hello'.") == []


class TestExtractCallRefs:
    def test_finds_call_statements(self):
        source = "CALL 'SUBPROG1'.\nCALL SUBPROG2."
        refs = _extract_call_refs(source)
        assert "SUBPROG1" in refs
        assert "SUBPROG2" in refs

    def test_empty_when_none(self):
        assert _extract_call_refs("DISPLAY 'hello'.") == []


class TestExtractParagraphs:
    def test_extracts_named_paragraph(self):
        source = (
            "PROCEDURE DIVISION.\n"
            "COMPUTE-INTEREST.\n"
            "    COMPUTE X = 1.\n"
            "    STOP RUN.\n"
        )
        paras = _extract_paragraphs(source, [], [], [])
        assert any(p["name"] == "COMPUTE-INTEREST" for p in paras)

    def test_falls_back_to_main_when_no_paragraphs(self):
        source = "PROCEDURE DIVISION.\n    DISPLAY 'hi'.\n"
        paras = _extract_paragraphs(source, [], [], [])
        assert paras[0]["name"] == "MAIN"

    def test_variables_attached_to_paragraphs(self):
        source = "PROCEDURE DIVISION.\nMAIN.\n    STOP RUN.\n"
        paras = _extract_paragraphs(source, ["WS-X"], [], [])
        assert "WS-X" in paras[0]["variables"]


class TestToRawUrl:
    def test_converts_blob_url(self):
        url = "https://github.com/owner/repo/blob/main/file.cbl"
        assert _to_raw_url(url) == "https://raw.githubusercontent.com/owner/repo/main/file.cbl"

    def test_raw_url_unchanged(self):
        url = "https://raw.githubusercontent.com/owner/repo/main/file.cbl"
        assert _to_raw_url(url) == url


class TestParseGithubRepoUrl:
    def test_standard_url(self):
        owner, repo = _parse_github_repo_url("https://github.com/owner/myrepo")
        assert owner == "owner"
        assert repo == "myrepo"

    def test_git_suffix_stripped(self):
        owner, repo = _parse_github_repo_url("https://github.com/owner/myrepo.git")
        assert repo == "myrepo"

    def test_trailing_slash_and_path(self):
        owner, repo = _parse_github_repo_url("https://github.com/owner/myrepo/tree/main")
        assert owner == "owner"
        assert repo == "myrepo"

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError):
            _parse_github_repo_url("https://gitlab.com/owner/repo")


# ── Integration tests (require API key) ───────────────────────────────────────

@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY") and not os.getenv("ANTHROPIC_API_KEY")
    and not os.getenv("GROQ_API_KEY") and not os.getenv("GROK_API_KEY")
    and not os.getenv("GEMINI_API_KEY"),
    reason="No LLM API key found in environment",
)
class TestRunMigrationIntegration:
    def test_produces_paragraphs(self):
        source = SAMPLE_COBOL.read_text()
        result = run_migration(source)
        assert len(result["paragraphs"]) > 0

    def test_paragraph_has_summary(self):
        source = SAMPLE_COBOL.read_text()
        result = run_migration(source)
        for p in result["paragraphs"]:
            assert p["summary"], f"Paragraph {p['name']} has no summary"

    def test_translated_code_is_python(self):
        source = SAMPLE_COBOL.read_text()
        result = run_migration(source)
        assert result["translated_code"]
        assert "def " in result["translated_code"] or "=" in result["translated_code"]

    def test_status_is_not_failed(self):
        source = SAMPLE_COBOL.read_text()
        result = run_migration(source)
        assert result["status"] != "failed", f"Pipeline failed: {result['error_log']}"

    def test_iteration_count_is_at_least_one(self):
        source = SAMPLE_COBOL.read_text()
        result = run_migration(source)
        assert result["iteration_count"] >= 1

    def test_file_path_stored(self):
        source = SAMPLE_COBOL.read_text()
        result = run_migration(source, file_path="tests/sample.cbl")
        assert result["file_path"] == "tests/sample.cbl"

    def test_copy_refs_detected(self):
        source = "IDENTIFICATION DIVISION.\nPROCEDURE DIVISION.\nMAIN.\n    COPY CUSTDATA.\n    STOP RUN.\n"
        result = run_migration(source)
        all_copy_refs = [r for p in result["paragraphs"] for r in p.get("copy_refs", [])]
        assert "CUSTDATA" in all_copy_refs
