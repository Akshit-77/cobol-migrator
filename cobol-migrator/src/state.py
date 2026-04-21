from typing import TypedDict, Optional


class MigrationState(TypedDict):
    """State for a single COBOL file moving through the pipeline."""
    source_code: str
    source_url: Optional[str]       # single raw file URL (github.com blob link)
    file_path: Optional[str]        # relative path inside repo, e.g. "src/INTEREST.cbl"
    paragraphs: list[dict]          # [{name, body, summary, variables, copy_refs, call_refs}]
    translated_code: str
    test_code: str
    test_results: dict              # {passed, failed, errors, total}
    lint_results: list[str]
    iteration_count: int
    max_iterations: int
    error_log: list[str]
    documentation: str
    confidence_score: float
    status: str                     # "parsing"|"translating"|"validating"|"done"|"failed"


class RepoMigrationResult(TypedDict):
    """Aggregate result when migrating an entire repository."""
    repo_url: str
    total_files: int
    completed_files: int
    failed_files: int
    files: list[MigrationState]     # one entry per COBOL file found
    unresolved_copies: list[str]    # COPY statements that could not be resolved
    unresolved_calls: list[str]     # CALL statements that cross file boundaries
    average_confidence: float
    status: str                     # "done"|"partial"|"failed"
