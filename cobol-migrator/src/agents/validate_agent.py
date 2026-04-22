import ast as ast_module
import os
import re
import subprocess
import sys
import tempfile
from src.state import MigrationState
from src.llm import chat


def _syntax_check(code: str) -> list[str]:
    try:
        ast_module.parse(code)
        return []
    except SyntaxError as e:
        return [f"SyntaxError: {e}"]


def _lint_check(code: str, tmpdir: str) -> list[str]:
    path = os.path.join(tmpdir, "translated.py")
    with open(path, "w") as f:
        f.write(code)
    result = subprocess.run(
        [sys.executable, "-m", "pyflakes", path],
        capture_output=True, text=True, timeout=10,
    )
    lines = (result.stdout + result.stderr).strip().splitlines()
    prefix = path + ":"
    return [ln.replace(prefix, "line ") for ln in lines if ln.strip()]


def _extract_function_names(code: str) -> list[str]:
    """Return top-level non-private function names from the translated code via AST."""
    try:
        tree = ast_module.parse(code)
        return [
            node.name for node in ast_module.walk(tree)
            if isinstance(node, ast_module.FunctionDef) and not node.name.startswith("_")
        ]
    except Exception:
        return []


def _generate_tests(state: MigrationState) -> tuple[str, list[str]]:
    """Return (test_body, fn_names).  The caller prepends the guaranteed import header."""
    fn_names = _extract_function_names(state["translated_code"])
    # Fall back to paragraph-name-derived names if AST yields nothing
    if not fn_names:
        fn_names = [p["name"].lower().replace("-", "_") for p in state["paragraphs"]]

    import_line = (
        f"from translated import {', '.join(fn_names)}"
        if fn_names else "import translated"
    )

    para_summaries = "\n".join(
        f"- {p['name']} → {p['name'].lower().replace('-', '_')}(): {p['summary']}"
        for p in state["paragraphs"]
    )

    prompt = (
        "Generate pytest test functions for the Python 3 code below.\n\n"
        "IMPORTANT: The following import is ALREADY written at the top of the test file — "
        "do NOT write it again:\n\n"
        f"    {import_line}\n\n"
        "RULES:\n"
        "1. Write ONLY test functions (starting with `test_`).\n"
        "2. Do NOT write any import statements — they are already present.\n"
        "3. Do NOT write `if __name__ == '__main__':` blocks.\n"
        "4. Use only Python standard library in assertions — no third-party packages.\n"
        "5. Write at least one test function per function listed below.\n"
        "6. Tests must be self-contained: no external files, no network, no stdin.\n"
        "7. Output ONLY a ```python ... ``` block containing the test functions.\n\n"
        f"Functions to test:\n{para_summaries}\n\n"
        f"Code under test:\n```python\n{state['translated_code']}\n```"
    )

    raw = chat(messages=[{"role": "user", "content": prompt}], max_tokens=2048)
    match = re.search(r"```python\n(.*?)```", raw, re.DOTALL)
    test_body = match.group(1).strip() if match else raw.strip()

    # Strip any `from translated import` / `import translated` lines the LLM added anyway
    test_body = "\n".join(
        ln for ln in test_body.splitlines()
        if not re.match(r"^\s*(from\s+translated\s+import|import\s+translated)", ln)
    )

    return test_body, fn_names


def _run_tests(translated_code: str, test_body: str, fn_names: list[str], tmpdir: str) -> dict:
    src_path = os.path.join(tmpdir, "translated.py")
    test_path = os.path.join(tmpdir, "test_translated.py")
    conftest_path = os.path.join(tmpdir, "conftest.py")

    import_line = (
        f"from translated import {', '.join(fn_names)}"
        if fn_names else "import translated"
    )

    # Guaranteed header injected before any LLM-generated code:
    # - sys.path ensures `import translated` resolves
    # - explicit import so test functions never hit NameError on the functions they call
    header = (
        f"import sys as _sys\n"
        f"_sys.path.insert(0, {tmpdir!r})\n"
        f"{import_line}\n\n"
    )

    with open(src_path, "w") as f:
        f.write(translated_code)
    with open(test_path, "w") as f:
        f.write(header + test_body)
    with open(conftest_path, "w") as f:
        f.write(f"import sys\nsys.path.insert(0, {tmpdir!r})\n")

    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = tmpdir + (os.pathsep + existing if existing else "")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header", "-q"],
        capture_output=True, text=True, timeout=30, cwd=tmpdir, env=env,
    )
    output = result.stdout + result.stderr

    passed = len(re.findall(r" PASSED", output))
    failed = len(re.findall(r" FAILED", output))
    errors = [
        ln for ln in output.splitlines()
        if any(kw in ln for kw in ("ERROR", "FAILED", "ImportError", "ModuleNotFoundError", "AttributeError"))
    ]
    total = passed + failed

    if total == 0:
        # Surface full pytest output so reflect agent can diagnose it
        short = "\n".join(output.strip().splitlines()[:12]) if output.strip() else "pytest produced no output"
        errors = errors or [f"No tests collected: {short}"]

    return {"passed": passed, "failed": failed, "errors": errors, "total": total}


def validate_agent(state: MigrationState) -> MigrationState:
    code = state["translated_code"]

    syntax_errors = _syntax_check(code)
    if syntax_errors:
        return {
            **state,
            "status": "validating",
            "lint_results": syntax_errors,
            "test_results": {"passed": 0, "failed": 0, "errors": syntax_errors, "total": 0},
            "error_log": state["error_log"] + [f"ValidateAgent syntax: {e}" for e in syntax_errors],
        }

    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            lint_results = _lint_check(code, tmpdir)
        except Exception as e:
            lint_results = [f"Lint error: {e}"]

        test_code = ""
        fn_names: list[str] = []
        try:
            test_code, fn_names = _generate_tests(state)
        except Exception as e:
            lint_results = lint_results + [f"TestGen error: {e}"]

        test_results: dict = {"passed": 0, "failed": 0, "errors": [], "total": 0}
        if test_code:
            try:
                test_results = _run_tests(code, test_code, fn_names, tmpdir)
            except subprocess.TimeoutExpired:
                test_results = {"passed": 0, "failed": 0, "errors": ["Tests timed out"], "total": 0}
            except Exception as e:
                test_results = {"passed": 0, "failed": 0, "errors": [str(e)], "total": 0}

    new_errors = lint_results + test_results.get("errors", [])
    error_log = state["error_log"] + ([f"ValidateAgent: {e}" for e in new_errors] if new_errors else [])

    return {
        **state,
        "status": "validating",
        "lint_results": lint_results,
        "test_results": test_results,
        "test_code": test_code,
        "error_log": error_log,
    }
