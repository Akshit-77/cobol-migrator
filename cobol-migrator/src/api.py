import uuid
from typing import Any

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from src.pipeline import run_migration, run_repo_migration, get_checkpointed_state
from src.llm import chat

app = FastAPI(title="COBOL Migrator API", version="0.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory job store: job_id → {"status", "result", "error"}
_jobs: dict[str, dict[str, Any]] = {}


# ── Models ─────────────────────────────────────────────────────────────────────

class MigrateRequest(BaseModel):
    source_code: str | None = None
    source_url:  str | None = None
    repo_url:    str | None = None


class JobCreated(BaseModel):
    job_id: str
    status: str


class JobStatus(BaseModel):
    job_id: str
    status: str
    result: dict | None = None
    error:  str  | None = None


# ── Background worker ─────────────────────────────────────────────────────────

def _run_job(job_id: str, request: MigrateRequest) -> None:
    try:
        if request.repo_url:
            result = run_repo_migration(request.repo_url)
        else:
            # Pass job_id as thread_id so LangGraph checkpoints state per job
            result = run_migration(
                source_code=request.source_code or "",
                source_url=request.source_url,
                thread_id=job_id,
            )
        _jobs[job_id]["result"] = dict(result)
        _jobs[job_id]["status"] = result.get("status", "done")
    except Exception as e:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["error"]  = str(e)


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health() -> dict:
    import os
    return {
        "status": "ok",
        "jobs": len(_jobs),
        "llm_provider": os.getenv("LLM_PROVIDER", "not set"),
    }


@app.get("/api/test-llm")
def test_llm() -> dict:
    """Make one tiny LLM call and return the result."""
    try:
        reply = chat(
            messages=[{"role": "user", "content": "Reply with the single word: working"}],
            max_tokens=10,
        )
        return {"status": "ok", "reply": reply.strip()}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.post("/api/migrate", response_model=JobCreated, status_code=202)
def migrate(request: MigrateRequest, background_tasks: BackgroundTasks) -> JobCreated:
    if not any([request.source_code, request.source_url, request.repo_url]):
        raise HTTPException(
            status_code=422,
            detail="Provide one of: source_code, source_url, or repo_url",
        )
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": "queued", "result": None, "error": None}
    background_tasks.add_task(_run_job, job_id, request)
    return JobCreated(job_id=job_id, status="queued")


@app.get("/api/status/{job_id}", response_model=JobStatus)
def status(job_id: str) -> JobStatus:
    job = _jobs.get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id!r} not found")
    return JobStatus(job_id=job_id, **job)


@app.get("/api/checkpoint/{job_id}")
def checkpoint(job_id: str) -> dict:
    """
    Return the latest LangGraph checkpoint for a job.
    Exposes agent state (paragraphs, reflection, fix_plan, error_log, …)
    so you can inspect what each agent produced without waiting for completion.
    """
    state = get_checkpointed_state(job_id)
    if state is None:
        raise HTTPException(status_code=404, detail=f"No checkpoint found for job {job_id!r}")
    return {
        "job_id": job_id,
        "status": state.get("status"),
        "iteration_count": state.get("iteration_count"),
        "confidence_score": state.get("confidence_score"),
        "reflection": state.get("reflection"),
        "fix_plan": state.get("fix_plan"),
        "error_log": state.get("error_log"),
        "lint_results": state.get("lint_results"),
        "test_results": state.get("test_results"),
        "paragraphs": [
            {"name": p["name"], "summary": p["summary"]}
            for p in state.get("paragraphs", [])
        ],
    }
