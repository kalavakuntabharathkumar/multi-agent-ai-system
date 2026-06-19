import json
import uuid
from core.executor import ExecutionEngine
from core.logger import get_logger
from api.database import SessionLocal
from api.models import Job

logger = get_logger()


def process_job(job_id: uuid.UUID) -> None:
    db = SessionLocal()
    try:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        job.status = "processing"
        db.commit()
        logger.info(f"Job {job_id} status → processing")

        engine = ExecutionEngine()
        result = engine.run(job.input_text)

        job.result = json.dumps(result)
        job.status = "done"
        logger.info(f"Job {job_id} status → done")
    except Exception as exc:
        logger.error(f"Job {job_id} failed: {exc}")
        if job:
            job.status = "failed"
            job.result = str(exc)
    finally:
        db.commit()
        db.close()
