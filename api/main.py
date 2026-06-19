import json
import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException, BackgroundTasks, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, Generator, Optional
from sqlalchemy.orm import Session

from core.executor import ExecutionEngine
from api.database import Base, engine, get_db
from api.models import Job
from api.job_worker import process_job

WORD_COUNT_THRESHOLD = int(os.environ.get("WORD_COUNT_THRESHOLD", "500"))

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Multi-Agent AI Task Automation API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class TaskRequest(BaseModel):
    task: str


@app.post("/api/run-task")
async def run_task(request: TaskRequest) -> Dict[str, Any]:
    if not request.task.strip():
        raise HTTPException(status_code=400, detail="task must not be empty")
    execution_engine = ExecutionEngine()
    result = execution_engine.run(request.task)
    return result


@app.get("/api/run-task/stream")
async def stream_task(
    task: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> Any:
    if not task.strip():
        raise HTTPException(status_code=400, detail="task query param must not be empty")

    word_count = len(task.split())

    if word_count > WORD_COUNT_THRESHOLD:
        job = Job(input_text=task, status="queued")
        db.add(job)
        db.commit()
        db.refresh(job)
        background_tasks.add_task(process_job, job.id)
        return {
            "queued": True,
            "job_id": str(job.id),
            "message": (
                f"Input exceeds {WORD_COUNT_THRESHOLD} words ({word_count} words). "
                f"Job queued. Poll GET /jobs/{job.id} for status."
            ),
        }

    def event_generator() -> Generator[str, None, None]:
        execution_engine = ExecutionEngine()
        for item in execution_engine.run_stream(task):
            event_type = item.get("event", "message")
            payload = json.dumps(item.get("data", {}))
            yield f"event: {event_type}\ndata: {payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/jobs/{job_id}")
async def get_job(job_id: str, db: Session = Depends(get_db)) -> Dict[str, Any]:
    try:
        parsed_id = uuid.UUID(job_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid job_id format")

    job = db.query(Job).filter(Job.id == parsed_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    result = None
    if job.result:
        try:
            result = json.loads(job.result)
        except json.JSONDecodeError:
            result = job.result

    return {
        "job_id": str(job.id),
        "status": job.status,
        "result": result,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "updated_at": job.updated_at.isoformat() if job.updated_at else None,
    }
