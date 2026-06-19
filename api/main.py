import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, Generator
from core.executor import ExecutionEngine

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
    engine = ExecutionEngine()
    result = engine.run(request.task)
    return result


@app.get("/api/run-task/stream")
async def stream_task(task: str) -> StreamingResponse:
    if not task.strip():
        raise HTTPException(status_code=400, detail="task query param must not be empty")

    def event_generator() -> Generator[str, None, None]:
        engine = ExecutionEngine()
        for item in engine.run_stream(task):
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
