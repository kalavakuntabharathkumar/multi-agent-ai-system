"""
LangGraph-based execution engine.

Orchestration flow:
  planner ──> worker ──[route_after_worker]──> worker  (retry, up to 3 attempts)
                                           └──> advance ──[route_after_advance]──> worker (next step)
                                                                               └──> END
Dependency-aware routing: a step is only started once all its `depends_on` /
`dependencies` entries are present in `completed_step_ids`.
"""

import time
from typing import Any, Dict, Generator, List

from langgraph.graph import StateGraph, END
from typing_extensions import TypedDict

from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from core.memory import Memory
from core.logger import get_logger

logger = get_logger()

# ── Shared agent instances (module-level so nodes can reference them) ─────────
_memory = Memory()
_planner = PlannerAgent()
_worker = WorkerAgent(_memory)


# ── Graph state ───────────────────────────────────────────────────────────────
class GraphState(TypedDict):
    task: str
    plan: Dict[str, Any]
    steps: List[Dict[str, Any]]
    current_step_index: int
    current_attempt: int
    trace: List[Dict[str, Any]]
    completed_step_ids: List[str]
    final_output: Dict[str, Any]


# ── Nodes ─────────────────────────────────────────────────────────────────────
def planner_node(state: GraphState) -> Dict[str, Any]:
    logger.info("planner_node: generating plan")
    plan = _planner.create_plan(state["task"])
    _memory.set_step_output("user_task", state["task"])
    return {
        "plan": plan,
        "steps": plan.get("steps", []),
        "current_step_index": 0,
        "current_attempt": 0,
        "trace": [],
        "completed_step_ids": [],
        "final_output": {},
    }


def worker_node(state: GraphState) -> Dict[str, Any]:
    steps = state["steps"]
    idx = state["current_step_index"]
    step = steps[idx]
    attempt = state["current_attempt"] + 1

    logger.info(f"worker_node: step {step['id']}, attempt {attempt}")
    start = time.time()
    result = _worker.execute_step(step)
    elapsed = round(time.time() - start, 2)

    result["attempt"] = attempt
    result["elapsed_seconds"] = elapsed

    return {
        "current_attempt": attempt,
        "trace": state["trace"] + [result],
    }


def advance_node(state: GraphState) -> Dict[str, Any]:
    """Mark the current step complete and find the next eligible step."""
    steps = state["steps"]
    idx = state["current_step_index"]
    step_id = steps[idx]["id"]
    completed = state["completed_step_ids"] + [step_id]

    next_idx = None
    for i, s in enumerate(steps):
        if s["id"] in completed:
            continue
        deps = s.get("depends_on", s.get("dependencies", [])) or []
        if all(d in completed for d in deps):
            next_idx = i
            break

    logger.info(
        f"advance_node: completed {step_id}, next_idx={next_idx}, "
        f"completed_so_far={completed}"
    )
    return {
        "current_step_index": next_idx if next_idx is not None else idx,
        "current_attempt": 0,
        "completed_step_ids": completed,
    }


# ── Routing functions ─────────────────────────────────────────────────────────
def route_after_worker(state: GraphState) -> str:
    """Retry same step (up to 3 attempts) or advance to the next step."""
    last_result = state["trace"][-1]
    attempt = state["current_attempt"]
    if last_result["status"] != "success" and attempt < 3:
        logger.info(f"route_after_worker: retrying (attempt {attempt})")
        return "retry"
    return "advance"


def route_after_advance(state: GraphState) -> str:
    """Route to next worker call or END when all steps are complete."""
    completed = state["completed_step_ids"]
    steps = state["steps"]
    remaining = [s for s in steps if s["id"] not in completed]
    if not remaining:
        logger.info("route_after_advance: all steps complete -> END")
        return "done"
    logger.info(f"route_after_advance: {len(remaining)} step(s) remaining -> worker")
    return "next"


# ── Build and compile the graph ───────────────────────────────────────────────
_builder = StateGraph(GraphState)
_builder.add_node("planner", planner_node)
_builder.add_node("worker", worker_node)
_builder.add_node("advance", advance_node)

_builder.set_entry_point("planner")
_builder.add_edge("planner", "worker")
_builder.add_conditional_edges(
    "worker",
    route_after_worker,
    {"retry": "worker", "advance": "advance"},
)
_builder.add_conditional_edges(
    "advance",
    route_after_advance,
    {"done": END, "next": "worker"},
)

execution_graph = _builder.compile()


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_initial_state(task: str) -> Dict[str, Any]:
    return {
        "task": task,
        "plan": {},
        "steps": [],
        "current_step_index": 0,
        "current_attempt": 0,
        "trace": [],
        "completed_step_ids": [],
        "final_output": {},
    }


def run(user_task: str) -> Dict[str, Any]:
    """Invoke the graph synchronously and return the full result."""
    logger.info("executor.run started (LangGraph)")
    final_state = execution_graph.invoke(_make_initial_state(user_task))
    logger.info("executor.run completed")
    return {
        "task": user_task,
        "plan": final_state["plan"],
        "trace": final_state["trace"],
        "final_output": _memory.get_context(),
    }


def run_stream(user_task: str) -> Generator[Dict[str, Any], None, None]:
    """Stream graph node outputs as SSE-compatible events."""
    logger.info("executor.run_stream started (LangGraph)")
    for chunk in execution_graph.stream(_make_initial_state(user_task)):
        for node_name, update in chunk.items():
            if node_name == "planner":
                yield {"event": "plan", "data": update.get("plan", {})}
            elif node_name == "worker":
                trace = update.get("trace", [])
                if trace:
                    yield {"event": "step", "data": trace[-1]}
            # advance_node updates are internal routing state — no SSE event
    final_output = _memory.get_context()
    logger.info("executor.run_stream completed")
    yield {"event": "done", "data": final_output}


# ── Backward-compatible ExecutionEngine wrapper ───────────────────────────────
class ExecutionEngine:
    """Thin wrapper kept for import compatibility. Delegates to execution_graph."""

    def run(self, user_task: str) -> Dict[str, Any]:
        return run(user_task)

    def run_stream(self, user_task: str) -> Generator[Dict[str, Any], None, None]:
        return run_stream(user_task)
