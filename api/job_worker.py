# Background job processor: runs a task through the ExecutionEngine and updates the Job row.
# Called as a FastAPI BackgroundTask for inputs that exceed the word-count threshold.

import json
import uuid
from core.executor import ExecutionEngine
from core.logger import get_logger
from api.database import SessionLocal
from api.models import Job

logger = get_logger()


def process_job(job_id: uuid.UUID) -> None:
    """Fetch the Job by id, run the task, and persist the result (or error) back to the database."""
    db = SessionLocal()  # open a new session for this background task (not shared with the request)
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return  # nothing to process — bail out early

        job.status = "processing"  # mark as in-progress so the status endpoint reflects it
        db.commit()
        logger.info(f"Job {job_id} status → processing")

        engine = ExecutionEngine()
        result = engine.run(job.input_text)  # run the full planner + worker pipeline

        job.result = json.dumps(result)  # serialize the result dict to a JSON string for storage
        job.status = "done"
        logger.info(f"Job {job_id} status → done")
    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}")
        if job:
            job.status = "failed"
            job.result = str(exc)  # store the error message so callers can see what went wrong
    finally:
        db.commit()  # persist status and result regardless of success or failure
        db.close()
