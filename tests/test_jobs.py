"""
Tests for the PostgreSQL job-queuing layer.

Run with:
    pytest tests/test_jobs.py -v
"""

import uuid
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.models import Job
from api.main import app, WORD_COUNT_THRESHOLD

SQLITE_URL = "sqlite:///./test_jobs.db"
test_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


client = TestClient(app)


def make_heavy_input(word_count: int = WORD_COUNT_THRESHOLD + 10) -> str:
    return " ".join(["word"] * word_count)


def make_light_input(word_count: int = 5) -> str:
    return " ".join(["word"] * word_count)


class TestJobCreation:
    """Heavy input (> threshold) creates a Job row with status 'queued'."""

    def test_heavy_input_creates_queued_job(self):
        heavy_task = make_heavy_input()

        with patch("api.main.process_job"):
            response = client.get(f"/api/run-task/stream?task={heavy_task}")

        assert response.status_code == 200
        body = response.json()
        assert body["queued"] is True
        assert "job_id" in body

        db = TestingSessionLocal()
        job = db.query(Job).filter(Job.id == uuid.UUID(body["job_id"])).first()
        db.close()

        assert job is not None
        assert job.status == "queued"
        assert job.input_text == heavy_task


class TestStatusCheckEndpoint:
    """GET /api/jobs/{job_id} returns current status and result."""

    def test_get_existing_job_returns_status(self):
        db = TestingSessionLocal()
        job = Job(input_text="some task", status="done", result='{"task": "some task"}')
        db.add(job)
        db.commit()
        job_id = str(job.id)
        db.close()

        response = client.get(f"/api/jobs/{job_id}")
        assert response.status_code == 200
        body = response.json()
        assert body["job_id"] == job_id
        assert body["status"] == "done"
        assert body["result"] == {"task": "some task"}

    def test_get_nonexistent_job_returns_404(self):
        response = client.get(f"/api/jobs/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_job_invalid_uuid_returns_400(self):
        response = client.get("/api/jobs/not-a-uuid")
        assert response.status_code == 400


class TestSizeThresholdRouting:
    """Light input streams SSE; heavy input creates a Job row and returns job_id."""

    def test_light_input_does_not_create_job(self):
        light_task = make_light_input()

        with patch("api.main.ExecutionEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine.run_stream.return_value = iter([
                {"event": "plan", "data": {"steps": []}},
                {"event": "done", "data": {}},
            ])
            mock_engine_cls.return_value = mock_engine

            response = client.get(f"/api/run-task/stream?task={light_task}")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        db = TestingSessionLocal()
        job_count = db.query(Job).count()
        db.close()
        assert job_count == 0

    def test_heavy_input_creates_job_light_does_not(self):
        heavy_task = make_heavy_input()
        light_task = make_light_input()

        with patch("api.main.process_job"):
            client.get(f"/api/run-task/stream?task={heavy_task}")

        with patch("api.main.ExecutionEngine") as mock_engine_cls:
            mock_engine = MagicMock()
            mock_engine.run_stream.return_value = iter([
                {"event": "done", "data": {}},
            ])
            mock_engine_cls.return_value = mock_engine
            client.get(f"/api/run-task/stream?task={light_task}")

        db = TestingSessionLocal()
        job_count = db.query(Job).count()
        db.close()
        assert job_count == 1
