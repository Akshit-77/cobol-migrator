import re
from src.state import MigrationState
from src.llm import chat


_SYSTEM_PROMPT = """You are an expert COBOL to Python 3 migration specialist.

Translation rules:
- COMPUTE X = Y      →  x = y  (only use Decimal for fields that actually have V99 / decimal places)
- MOVE X TO Y        →  y = x
- DISPLAY "text"     →  print("text")
- PERFORM PARA       →  call the equivalent Python function
- IF X > Y ... END-IF  →  if x > y: ...
- PERFORM UNTIL C    →  while not C: ...
- ADD 1 TO X         →  x += 1
- COBOL-KEBAB-CASE   →  python_snake_case  for all identifiers
- COPY / CALL refs that could not be resolved →  leave a  # TODO: resolve <NAME>  stub
- Only import what you actually use. Do NOT add unused imports.

Output a single complete Python 3 module inside a ```python ... ``` block. No explanation outside the block."""


def _build_prompt(state: MigrationState) -> str:
    para_text = "\n\n".join(
        f"Paragraph: {p['name']}\nPurpose: {p['summary']}\n{p['body']}"
        for p in state["paragraphs"]
    )

    unresolved = ""
    all_copy = [r for p in state["paragraphs"] for r in p.get("copy_refs", [])]
    all_call = [r for p in state["paragraphs"] for r in p.get("call_refs", [])]
    if all_copy or all_call:
        unresolved = (
            "\nUnresolved references (add TODO stubs):\n"
            + (f"  COPY: {', '.join(set(all_copy))}\n" if all_copy else "")
            + (f"  CALL: {', '.join(set(all_call))}\n" if all_call else "")
        )

    error_context = ""
    if state["error_log"] and state["iteration_count"] > 0:
        error_context = "\nPrevious attempt failed. Fix these errors:\n" + "\n".join(state["error_log"][-5:])

    return (
        f"Translate the following COBOL source to Python 3.\n\n"
        f"Source COBOL:\n{state['source_code']}\n\n"
        f"Extracted paragraphs:\n{para_text}"
        f"{unresolved}"
        f"{error_context}"
    )


def _strip_unused_imports(code: str) -> str:
    """Remove import lines flagged as unused by pyflakes."""
    import subprocess, sys, tempfile, os
    try:
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(code)
            tmp = f.name
        result = subprocess.run(
            [sys.executable, "-m", "pyflakes", tmp],
            capture_output=True, text=True, timeout=10,
        )
        os.unlink(tmp)
        unused: set[str] = set()
        for line in result.stdout.splitlines():
            m = re.search(r"'([^']+)' imported but unused", line)
            if m:
                unused.add(m.group(1).split(".")[0])  # top-level module name
        if not unused:
            return code
        cleaned = []
        for line in code.splitlines():
            # Remove the whole import line if it only imports unused names
            if re.match(r"^\s*(import|from)\s+", line):
                if any(name in line for name in unused):
                    continue
            cleaned.append(line)
        return "\n".join(cleaned)
    except Exception:
        return code


def translate_agent(state: MigrationState) -> MigrationState:
    try:
        raw = chat(
            messages=[{"role": "user", "content": _build_prompt(state)}],
            system=_SYSTEM_PROMPT,
            max_tokens=4096,
        )

        match = re.search(r"```python\n(.*?)```", raw, re.DOTALL)
        translated = match.group(1).strip() if match else raw.strip()
        translated = _strip_unused_imports(translated)

        return {
            **state,
            "translated_code": translated,
            "iteration_count": state["iteration_count"] + 1,
            "status": "translating",
        }

    except Exception as e:
        return {**state, "error_log": state["error_log"] + [f"TranslateAgent: {e}"]}
