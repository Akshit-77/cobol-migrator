"""
Stage 3 tests — Validate Agent, Document Agent, and self-correction loop.

Pure unit tests run without any LLM or network access.
Integration tests (marked) require a valid LLM API key in .env.

Run with: uv run pytest tests/test_stage3.py -v
"""
import ast
import os
import textwrap
import pytest

from src.agents.validate_agent import _syntax_check, _lint_check
from src.agents.document_agent import _compute_confidence, _build_mapping_table
from src.pipeline import _should_retry


# ── Helpers ───────────────────────────────────────────────────────────────────

def _make_state(**overrides) -> dict:
    """Return a minimal MigrationState-shaped dict."""
    base = {
        "source_code": "",
        "source_url": None,
        "file_path": None,
        "paragraphs": [],
        "translated_code": "",
        "test_code": "",
        "test_results": {"passed": 0, "failed": 0, "errors": [], "total": 0},
        "lint_results": [],
        "iteration_count": 0,
        "max_iterations": 3,
        "error_log": [],
        "documentation": "",
        "confidence_score": 0.0,
        "status": "translating",
    }
    base.update(overrides)
    return base


# ── _syntax_check ─────────────────────────────────────────────────────────────

class TestSyntaxCheck:
    def test_valid_code_returns_empty(self):
        assert _syntax_check("x = 1\nprint(x)") == []

    def test_invalid_code_returns_error(self):
        errors = _syntax_check("def foo(\n    pass")
        assert len(errors) > 0
        assert any("SyntaxError" in e for e in errors)

    def test_empty_string_is_valid(self):
        assert _syntax_check("") == []

    def test_multiline_function_valid(self):
        code = textwrap.dedent("""\
            def compute_interest(principal, rate, years):
                interest = principal * rate / 100 * years
                if interest > 10000:
                    interest = 10000
                return interest
        """)
        assert _syntax_check(code) == []

    def test_undefined_name_not_a_syntax_error(self):
        # ast.parse only checks syntax, not name resolution
        assert _syntax_check("result = undefined_var + 1") == []


# ── _lint_check ───────────────────────────────────────────────────────────────

class TestLintCheck:
    def test_clean_code_returns_empty(self, tmp_path):
        code = "x = 1\nprint(x)\n"
        result = _lint_check(code, str(tmp_path))
        assert result == []

    def test_unused_import_flagged(self, tmp_path):
        code = "import os\nx = 1\n"
        result = _lint_check(code, str(tmp_path))
        assert len(result) > 0
        assert any("os" in line for line in result)

    def test_undefined_name_flagged(self, tmp_path):
        code = "print(undefined_name)\n"
        result = _lint_check(code, str(tmp_path))
        assert len(result) > 0

    def test_path_prefix_stripped(self, tmp_path):
        code = "import sys\n"
        result = _lint_check(code, str(tmp_path))
        # Result lines should NOT contain the full temp path
        for line in result:
            assert str(tmp_path) not in line


# ── _compute_confidence ───────────────────────────────────────────────────────

class TestComputeConfidence:
    def test_all_pass_no_lint_gives_full_score(self):
        state = _make_state(
            test_results={"passed": 5, "failed": 0, "errors": [], "total": 5},
            lint_results=[],
        )
        assert _compute_confidence(state) == 1.0

    def test_all_pass_with_lint_gives_70_percent(self):
        state = _make_state(
            test_results={"passed": 3, "failed": 0, "errors": [], "total": 3},
            lint_results=["line 1: unused import"],
        )
        assert _compute_confidence(state) == pytest.approx(0.7)

    def test_no_tests_no_lint_gives_30_percent(self):
        state = _make_state(
            test_results={"passed": 0, "failed": 0, "errors": [], "total": 0},
            lint_results=[],
        )
        assert _compute_confidence(state) == pytest.approx(0.3)

    def test_half_pass_no_lint(self):
        state = _make_state(
            test_results={"passed": 2, "failed": 2, "errors": [], "total": 4},
            lint_results=[],
        )
        # 0.5 * 0.7 + 1.0 * 0.3 = 0.35 + 0.30 = 0.65
        assert _compute_confidence(state) == pytest.approx(0.65)

    def test_score_clamped_to_two_decimal_places(self):
        state = _make_state(
            test_results={"passed": 1, "failed": 2, "errors": [], "total": 3},
            lint_results=[],
        )
        score = _compute_confidence(state)
        assert score == round(score, 2)


# ── _build_mapping_table ──────────────────────────────────────────────────────

class TestBuildMappingTable:
    def test_produces_markdown_table(self):
        state = _make_state(paragraphs=[
            {"name": "COMPUTE-INTEREST", "summary": "Computes interest", "body": ""},
        ])
        table = _build_mapping_table(state)
        assert "| COBOL Paragraph |" in table
        assert "COMPUTE-INTEREST" in table
        assert "compute_interest()" in table

    def test_kebab_converted_to_snake(self):
        state = _make_state(paragraphs=[
            {"name": "READ-CUSTOMER-DATA", "summary": "Reads customer data", "body": ""},
        ])
        table = _build_mapping_table(state)
        assert "read_customer_data()" in table

    def test_empty_paragraphs_still_has_header(self):
        state = _make_state(paragraphs=[])
        table = _build_mapping_table(state)
        assert "| COBOL Paragraph |" in table

    def test_multiple_paragraphs_all_appear(self):
        state = _make_state(paragraphs=[
            {"name": "INIT", "summary": "Initializes values", "body": ""},
            {"name": "PROCESS", "summary": "Processes records", "body": ""},
            {"name": "CLEANUP", "summary": "Cleans up", "body": ""},
        ])
        table = _build_mapping_table(state)
        assert "INIT" in table
        assert "PROCESS" in table
        assert "CLEANUP" in table


# ── _should_retry (pipeline routing) ─────────────────────────────────────────

class TestShouldRetry:
    def test_routes_to_document_when_all_pass_no_lint(self):
        state = _make_state(
            test_results={"passed": 3, "failed": 0, "errors": [], "total": 3},
            lint_results=[],
            iteration_count=1,
            max_iterations=3,
        )
        assert _should_retry(state) == "document"

    def test_routes_to_translate_on_failures(self):
        state = _make_state(
            test_results={"passed": 1, "failed": 2, "errors": [], "total": 3},
            lint_results=["unused import"],
            iteration_count=1,
            max_iterations=3,
        )
        assert _should_retry(state) == "translate"

    def test_routes_to_document_at_max_iterations(self):
        state = _make_state(
            test_results={"passed": 0, "failed": 3, "errors": [], "total": 3},
            lint_results=["bad code"],
            iteration_count=3,
            max_iterations=3,
        )
        assert _should_retry(state) == "document"

    def test_routes_to_document_when_no_tests_run_but_no_lint(self):
        # total=0 means all_passed is False (no tests ran) — should retry
        state = _make_state(
            test_results={"passed": 0, "failed": 0, "errors": [], "total": 0},
            lint_results=[],
            iteration_count=1,
            max_iterations=3,
        )
        assert _should_retry(state) == "translate"

    def test_lint_errors_alone_cause_retry(self):
        state = _make_state(
            test_results={"passed": 3, "failed": 0, "errors": [], "total": 3},
            lint_results=["line 1: undefined name 'x'"],
            iteration_count=1,
            max_iterations=3,
        )
        assert _should_retry(state) == "translate"


# ── Integration tests ─────────────────────────────────────────────────────────

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
class TestValidateAgentIntegration:
    def test_full_pipeline_produces_confidence_score(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        assert result["confidence_score"] >= 0.0
        assert result["confidence_score"] <= 1.0

    def test_translated_code_is_syntactically_valid(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        assert result["translated_code"], "No translated code produced"
        errors = _syntax_check(result["translated_code"])
        assert errors == [], f"Translated code has syntax errors: {errors}"

    def test_documentation_produced(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        assert result["documentation"]
        assert "Migration Report" in result["documentation"]

    def test_documentation_contains_mapping_table(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        assert "COBOL Paragraph" in result["documentation"]

    def test_iteration_count_in_range(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        assert 1 <= result["iteration_count"] <= result["max_iterations"]

    def test_status_is_done(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        assert result["status"] == "done", f"Pipeline status: {result['status']}, errors: {result['error_log']}"

    def test_test_results_structure(self):
        from src.pipeline import run_migration
        result = run_migration(_SAMPLE_COBOL)
        tr = result["test_results"]
        assert "passed" in tr
        assert "failed" in tr
        assert "total" in tr
        assert tr["total"] == tr["passed"] + tr["failed"]
