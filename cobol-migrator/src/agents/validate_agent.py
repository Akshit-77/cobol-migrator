import ast
import os
import subprocess
import sys
import tempfile
from src.state import MigrationState
from src.llm import chat


def _syntax_check(code: str) -> list[str]:
    try:
        ast.parse(code)
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
    # Strip the temp path prefix so messages are readable
    prefix = path + ":"
    return [ln.replace(prefix, "line ") for ln in lines if ln.strip()]


def _generate_tests(state: MigrationState) -> str:
    fn_names = [p["name"].lower().replace("-", "_") for p in state["paragraphs"]]
    para_summaries = "\n".join(
        f"- {p['name']}: {p['summary']}" for p in state["paragraphs"]
    )
    prompt = (
        "Generate a pytest test module for the Python 3 code below.\n\n"
        "STRICT RULES:\n"
        "1. The code lives in a file called `translated.py`. Import from it like: "
        f"  `from translated import {', '.join(fn_names) or 'main'}`\n"
        "2. Do NOT use `if __name__ == '__main__':` in the test file.\n"
        "3. Use only the Python standard library and pytest — no other packages.\n"
        "4. Write at least one test function per function in the code.\n"
        "5. Tests must be runnable without any external setup or files.\n"
        "6. Output ONLY a ```python ... ``` block — nothing else.\n\n"
        f"Function purposes:\n{para_summaries}\n\n"
        f"Code to test:\n```python\n{state['translated_code']}\n```"
    )
    raw = chat(
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2048,
    )
    import re
    match = re.search(r"```python\n(.*?)```", raw, re.DOTALL)
    return match.group(1).strip() if match else raw.strip()


def _run_tests(translated_code: str, test_code: str, tmpdir: str) -> dict:
    src_path = os.path.join(tmpdir, "translated.py")
    test_path = os.path.join(tmpdir, "test_translated.py")
    # conftest.py puts tmpdir on sys.path so `import translated` always works
    conftest_path = os.path.join(tmpdir, "conftest.py")

    with open(src_path, "w") as f:
        f.write(translated_code)
    with open(test_path, "w") as f:
        f.write(test_code)
    with open(conftest_path, "w") as f:
        f.write(f"import sys\nsys.path.insert(0, {tmpdir!r})\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = tmpdir

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, "-v", "--tb=short", "--no-header", "-q"],
        capture_output=True, text=True, timeout=30, cwd=tmpdir, env=env,
    )
    output = result.stdout + result.stderr

    import re
    passed = len(re.findall(r" PASSED", output))
    failed = len(re.findall(r" FAILED", output))
    # Capture collection errors so the self-correction loop can see them
    errors = [ln for ln in output.splitlines()
              if "ERROR" in ln or "FAILED" in ln or "ImportError" in ln or "ModuleNotFoundError" in ln]
    total = passed + failed

    # If nothing ran at all, treat the full output as an error so the loop can fix it
    if total == 0 and output.strip():
        short = "\n".join(output.strip().splitlines()[:6])
        errors = errors or [f"No tests collected: {short}"]

    return {"passed": passed, "failed": failed, "errors": errors, "total": total}


def validate_agent(state: MigrationState) -> MigrationState:
    code = state["translated_code"]

    # Step 1: syntax check — if it fails, no point running anything else
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
        # Step 2: pyflakes lint
        try:
            lint_results = _lint_check(code, tmpdir)
        except Exception as e:
            lint_results = [f"Lint error: {e}"]

        # Step 3: generate pytest tests
        try:
            test_code = _generate_tests(state)
        except Exception as e:
            test_code = ""
            lint_results = lint_results + [f"TestGen error: {e}"]

        # Step 4: run tests
        test_results: dict = {"passed": 0, "failed": 0, "errors": [], "total": 0}
        if test_code:
            try:
                test_results = _run_tests(code, test_code, tmpdir)
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
