# FastAPI application entry point: exposes three endpoints for task execution.
# POST /api/run-task: synchronous execution; GET /api/run-task/stream: SSE streaming
# (queues heavy tasks as background jobs); GET /api/jobs/{job_id}: job status polling.

import json
import os
import sys
import uuid

# Ensure the project root is on sys.path so core/api/agents packages are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, Generator

from sqlalchemy.orm import Session

from core.executor import execution_graph, _make_initial_state, _memory
from api.database import Base, engine, get_db
from api.models import Job
from api.job_worker import process_job

# Tasks with more words than this threshold are queued instead of streamed inline
WORD_COUNT_THRESHOLD = int(os.environ.get("WORD_COUNT_THRESHOLD", "500"))

# Create database tables on startup if they don't already exist
Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multi-Agent AI Task Automation API", version="1.0.0")

# Allow all origins so the frontend (any host) can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    task: str  # the plain-text task description submitted by the user


@app.post("/api/run-task")
async def run_task(request: TaskRequest) -> Dict[str, Any]:
    """Run a task synchronously and return the complete result in one JSON response."""
    if not request.task.strip():
        raise HTTPException(status_code=400, detail="task must not be empty")
    final_state = execution_graph.invoke(_make_initial_state(request.task))  # run the full graph
    return {
        "task": request.task,
        "plan": final_state["plan"],
        "trace": final_state["trace"],
        "final_output": _memory.get_context(),  # all step outputs accumulated in memory
    }


@app.get("/api/run-task/stream")
async def stream_task(
    task: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Any:
    """Stream task execution as Server-Sent Events, or queue it if the input is too long."""
    if not task.strip():
        raise HTTPException(status_code=400, detail="task query param must not be empty")

    word_count = len(task.split())

    if word_count > WORD_COUNT_THRESHOLD:
        # Input is too large to stream inline — persist as a Job and process in background
        job = Job(input_text=task, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)  # populate the auto-generated id
        background_tasks.add_task(process_job, job.id)  # run the job after the response is sent
        return {
            "queued": True,
            "job_id": str(job.id),
            "message": (
                f"Input exceeds {WORD_COUNT_THRESHOLD} words ({word_count} words). "
                f"Job queued. Poll GET /jobs/{job.id} for status."
            ),
        }

    def event_generator() -> Generator[str, None, None]:
        """Yield SSE-formatted strings for each graph node update."""
        for chunk in execution_graph.stream(_make_initial_state(task)):
            for node_name, update in chunk.items():
                if node_name == "planner":
                    payload = json.dumps(update.get("plan", {}))
                    yield f"event: plan\ndata: {payload}\n\n"  # send the generated plan
                elif node_name == "worker":
                    trace = update.get("trace", [])
                    if trace:
                        yield f"event: step\ndata: {json.dumps(trace[-1])}\n\n"  # send latest step result
        yield f"event: done\ndata: {json.dumps(_memory.get_context())}\n\n"  # signal completion

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",       # prevent proxies from buffering the stream
            "X-Accel-Buffering": "no",          # disable nginx buffering for SSE
        },
    )


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    """Return the current status and result of a background job by its UUID."""
    try:
        parsed_id = uuid.UUID(job_id)  # validate that the path param is a valid UUID
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job = db.query(Job).filter(Job.id == parsed_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = None
    if job.result:
        try:
            result = json.loads(job.result)  # deserialize stored JSON string back to a dict
        except json.JSONDecodeError:
            result = job.result  # return raw string if it isn't valid JSON

    return {
        "job_id": str(job.id),
        "status": job.status,
        "result": result,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
