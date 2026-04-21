import re
from src.state import MigrationState
from src.llm import chat


_SYSTEM_PROMPT = """You are an expert COBOL to Python 3 migration specialist.

Translation rules:
- COMPUTE X = Y      →  x = y  (use Decimal for any PIC 9...V99 financial fields)
- MOVE X TO Y        →  y = x
- DISPLAY "text"     →  print("text")
- PERFORM PARA       →  call the equivalent Python function
- IF X > Y ... END-IF  →  if x > y: ...
- COBOL-KEBAB-CASE   →  python_snake_case  for all identifiers
- COPY / CALL refs that could not be resolved →  leave a  # TODO: resolve <NAME>  stub

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


def translate_agent(state: MigrationState) -> MigrationState:
    try:
        raw = chat(
            messages=[{"role": "user", "content": _build_prompt(state)}],
            system=_SYSTEM_PROMPT,
            max_tokens=4096,
        )

        match = re.search(r"```python\n(.*?)```", raw, re.DOTALL)
        translated = match.group(1).strip() if match else raw.strip()

        return {
            **state,
            "translated_code": translated,
            "iteration_count": state["iteration_count"] + 1,
            "status": "translating",
        }

    except Exception as e:
        return {**state, "error_log": state["error_log"] + [f"TranslateAgent: {e}"]}
