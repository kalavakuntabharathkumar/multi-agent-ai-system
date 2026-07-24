"""
Tests for the job-queuing layer and LangGraph orchestration.

Run with:
    pytest tests/test_jobs.py -v
"""

# Covers: job creation on heavy input, status endpoint, size-threshold routing,
# and LangGraph graph behavior (retries, dependency ordering, parallelism).

import uuid
import pytest
from unittest.mock import patch, MagicMock, call
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.database import Base, get_db
from api.models import Job
from api.main import app, WORD_COUNT_THRESHOLD

# Use an in-memory SQLite database so tests don't touch the real PostgreSQL instance
SQLITE_URL = "sqlite:///./test_jobs.db"
test_engine = create_engine(SQLITE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)


def override_get_db():
    """FastAPI dependency override that uses the SQLite test session instead of PostgreSQL."""
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(autouse=True)
def setup_db():
    """Create tables before each test and drop them after, ensuring a clean slate."""
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db  # replace real DB with test DB
    yield
    Base.metadata.drop_all(bind=test_engine)
    app.dependency_overrides.clear()


client = TestClient(app)


def make_heavy_input(word_count: int = WORD_COUNT_THRESHOLD + 10) -> str:
    """Build a task string that exceeds the word-count threshold to trigger job queuing."""
    return " ".join(["word"] * word_count)


def make_light_input(word_count: int = 5) -> str:
    """Build a short task string that stays below the threshold to trigger inline streaming."""
    return " ".join(["word"] * word_count)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _stream_chunks_for(plan=None, steps=None):
    """Return a minimal stream chunk sequence for a mocked graph."""
    plan = plan or {"steps": []}
    steps = steps or []
    planner_update = {
        "plan": plan,
        "steps": steps,
        "current_step_index": 0,
        "current_attempt": 0,
        "trace": [],
        "completed_step_ids": [],
        "final_output": {},
    }
    return iter([{"planner": planner_update}])  # single planner chunk, no worker chunks


# ── Job creation tests ────────────────────────────────────────────────────────
class TestJobCreation:
    """Heavy input (> threshold) creates a Job row with status 'queued'."""

    def test_heavy_input_creates_queued_job(self):
        heavy_task = make_heavy_input()

        with patch("api.main.process_job"):  # don't actually run the background job
            response = client.get(f"/api/run-task/stream?task={heavy_task}")

        assert response.status_code == 200
        body = response.json()
        assert body["queued"] is True  # response must signal that the task was queued
        assert "job_id" in body

        db = TestingSessionLocal()
        job = db.query(Job).filter(Job.id == uuid.UUID(body["job_id"])).first()
        db.close()

        assert job is not None
        assert job.status == "queued"   # initial status must be "queued"
        assert job.input_text == heavy_task


# ── Status check endpoint tests ───────────────────────────────────────────────
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
        assert body["result"] == {"task": "some task"}  # result should be deserialized JSON

    def test_get_nonexistent_job_returns_404(self):
        response = client.get(f"/api/jobs/{uuid.uuid4()}")
        assert response.status_code == 404

    def test_get_job_invalid_uuid_returns_400(self):
        response = client.get("/api/jobs/not-a-uuid")
        assert response.status_code == 400  # malformed UUID should be rejected


# ── Size threshold routing tests ──────────────────────────────────────────────
class TestSizeThresholdRouting:
    """Light input streams SSE; heavy input creates a Job row and returns job_id."""

    def test_light_input_does_not_create_job(self):
        light_task = make_light_input()

        with patch("api.main.execution_graph") as mock_graph, \
             patch("api.main._memory") as mock_mem:
            mock_graph.stream.return_value = _stream_chunks_for()
            mock_mem.get_context.return_value = {}

            response = client.get(f"/api/run-task/stream?task={light_task}")

        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]  # must be SSE

        db = TestingSessionLocal()
        job_count = db.query(Job).count()
        db.close()
        assert job_count == 0  # no job row should be created for light input

    def test_heavy_input_creates_job_light_does_not(self):
        heavy_task = make_heavy_input()
        light_task = make_light_input()

        with patch("api.main.process_job"):
            client.get(f"/api/run-task/stream?task={heavy_task}")  # creates 1 job

        with patch("api.main.execution_graph") as mock_graph, \
             patch("api.main._memory") as mock_mem:
            mock_graph.stream.return_value = _stream_chunks_for()
            mock_mem.get_context.return_value = {}
            client.get(f"/api/run-task/stream?task={light_task}")  # should NOT create a job

        db = TestingSessionLocal()
        job_count = db.query(Job).count()
        db.close()
        assert job_count == 1  # only the heavy task should have created a job row


# ── LangGraph orchestration tests ─────────────────────────────────────────────
class TestLangGraphOrchestration:
    """Verify graph structure: node order, retries, and dependency-aware routing."""

    def _make_step(self, step_id: str, deps=None) -> dict:
        return {
            "id": step_id,
            "tool": "summarize",
            "description": f"Step {step_id}",
            "dependencies": deps or [],
        }

    def _success_result(self, step_id: str) -> dict:
        return {
            "id": step_id,
            "tool": "summarize",
            "result": "ok",
            "status": "success",
            "confidence": 0.9,
        }

    def _failure_result(self, step_id: str) -> dict:
        return {
            "id": step_id,
            "tool": "summarize",
            "result": "error",
            "status": "failed",
            "confidence": 0.1,
        }

    def test_graph_executes_planner_then_worker(self):
        """Planner node runs before worker; a single-step plan completes in one worker call."""
        with patch("core.executor._planner") as mock_planner, \
             patch("core.executor._worker") as mock_worker, \
             patch("core.executor._memory"):

            mock_planner.create_plan.return_value = {
                "steps": [self._make_step("s1")]
            }
            mock_worker.execute_step.return_value = self._success_result("s1")

            from core.executor import execution_graph, _make_initial_state
            result = execution_graph.invoke(_make_initial_state("test task"))

        mock_planner.create_plan.assert_called_once_with("test task")
        mock_worker.execute_step.assert_called_once()
        assert len(result["trace"]) == 1
        assert result["trace"][0]["status"] == "success"
        assert result["trace"][0]["attempt"] == 1

    def test_graph_retries_failed_step_up_to_3_times(self):
        """Worker retries a failing step exactly 3 times then moves on."""
        with patch("core.executor._planner") as mock_planner, \
             patch("core.executor._worker") as mock_worker, \
             patch("core.executor._memory"):

            mock_planner.create_plan.return_value = {
                "steps": [self._make_step("s1")]
            }
            mock_worker.execute_step.return_value = self._failure_result("s1")

            from core.executor import execution_graph, _make_initial_state
            result = execution_graph.invoke(_make_initial_state("failing task"))

        assert mock_worker.execute_step.call_count == 3  # must retry exactly 3 times
        assert len(result["trace"]) == 3
        assert all(t["status"] == "failed" for t in result["trace"])
        assert [t["attempt"] for t in result["trace"]] == [1, 2, 3]

    def test_graph_succeeds_on_second_attempt(self):
        """Worker retries once and succeeds; only 2 trace entries."""
        with patch("core.executor._planner") as mock_planner, \
             patch("core.executor._worker") as mock_worker, \
             patch("core.executor._memory"):

            mock_planner.create_plan.return_value = {
                "steps": [self._make_step("s1")]
            }
            mock_worker.execute_step.side_effect = [
                self._failure_result("s1"),  # first attempt fails
                self._success_result("s1"),  # second attempt succeeds
            ]

            from core.executor import execution_graph, _make_initial_state
            result = execution_graph.invoke(_make_initial_state("retry-once task"))

        assert mock_worker.execute_step.call_count == 2
        assert result["trace"][0]["status"] == "failed"
        assert result["trace"][1]["status"] == "success"

    def test_graph_respects_step_dependencies(self):
        """A step with a dependency only runs after that dependency completes."""
        execution_order = []

        def fake_execute(step):
            execution_order.append(step["id"])  # record the order steps are actually run
            return self._success_result(step["id"])

        with patch("core.executor._planner") as mock_planner, \
             patch("core.executor._worker") as mock_worker, \
             patch("core.executor._memory"):

            mock_planner.create_plan.return_value = {
                "steps": [
                    self._make_step("s1", deps=[]),
                    self._make_step("s2", deps=["s1"]),
                    self._make_step("s3", deps=["s2"]),
                ]
            }
            mock_worker.execute_step.side_effect = fake_execute

            from core.executor import execution_graph, _make_initial_state
            result = execution_graph.invoke(_make_initial_state("chained task"))

        assert execution_order == ["s1", "s2", "s3"]  # must run in dependency order
        assert len(result["trace"]) == 3
        assert all(t["status"] == "success" for t in result["trace"])

    def test_graph_parallel_steps_after_shared_dependency(self):
        """Two steps that both depend on s1 both run after s1 completes."""
        execution_order = []

        def fake_execute(step):
            execution_order.append(step["id"])
            return self._success_result(step["id"])

        with patch("core.executor._planner") as mock_planner, \
             patch("core.executor._worker") as mock_worker, \
             patch("core.executor._memory"):

            mock_planner.create_plan.return_value = {
                "steps": [
                    self._make_step("s1", deps=[]),
                    self._make_step("s2", deps=["s1"]),
                    self._make_step("s3", deps=["s1"]),
                ]
            }
            mock_worker.execute_step.side_effect = fake_execute

            from core.executor import execution_graph, _make_initial_state
            result = execution_graph.invoke(_make_initial_state("fan-out task"))

        # s1 must be first; s2 and s3 can run in either order after s1
        assert execution_order[0] == "s1"
        assert set(execution_order[1:]) == {"s2", "s3"}
        assert len(result["trace"]) == 3
