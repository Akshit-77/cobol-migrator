from src.state import MigrationState
from src.llm import chat


def reflect_agent(state: MigrationState) -> MigrationState:
    """
    Reasoning agent that diagnoses validation failures and writes a structured,
    actionable fix plan for the translate agent to follow on the next attempt.

    This is the "memory" step of the agentic loop: it converts raw error output
    into targeted instructions, preventing the next translation from repeating
    the same mistakes.
    """
    test_results = state["test_results"]
    lint_results = state["lint_results"]

    # Build a structured problem description
    problems: list[str] = []

    if lint_results:
        problems.append("## Lint / Static Analysis Errors\n" + "\n".join(f"  - {e}" for e in lint_results))

    if test_results.get("failed", 0) > 0:
        problems.append(
            f"## Test Failures\n"
            f"  {test_results['failed']} out of {test_results['total']} tests failed."
        )

    if test_results.get("errors"):
        problems.append(
            "## Test Runtime / Collection Errors\n"
            + "\n".join(f"  - {e}" for e in test_results["errors"][:8])
        )

    if not problems:
        # Nothing to reflect on — should not normally happen since reflect only
        # runs when _should_retry returned "reflect"
        return {
            **state,
            "status": "reflecting",
            "reflection": "No issues found.",
            "fix_plan": "",
        }

    prompt = f"""You are an expert Python debugger helping fix a COBOL → Python 3 migration.

## Original COBOL paragraph summaries
{chr(10).join(f"  - {p['name']}: {p['summary']}" for p in state['paragraphs'])}

## Current translated Python code (iteration {state['iteration_count']})
```python
{state['translated_code'][:3000]}
```

## Problems detected
{chr(10).join(problems)}

## Previous fix attempts
{state['reflection'] or 'None — this is the first reflection.'}

---
Your task: Write a SPECIFIC, ACTIONABLE fix plan as a numbered list.

For each problem:
1. Name the root cause (e.g., wrong return type, missing function, bad import)
2. State exactly what to change (e.g., "change `return ws_interest` to `return float(ws_interest)`")
3. Explain why the fix is correct in terms of the original COBOL semantics

Be precise. Reference actual variable names and line patterns from the code above.
Do not repeat fixes that were already attempted.
Output only the numbered fix plan — no preamble, no summary."""

    try:
        fix_plan = chat(
            messages=[{"role": "user", "content": prompt}],
            max_tokens=1024,
        ).strip()
    except Exception as e:
        fix_plan = f"Reflection failed: {e}"

    iteration_tag = f"Iteration {state['iteration_count']}"
    return {
        **state,
        "status": "reflecting",
        "reflection": fix_plan,
        "fix_plan": fix_plan,
        "error_log": state["error_log"] + [f"ReflectAgent [{iteration_tag}]: fix plan generated"],
    }
