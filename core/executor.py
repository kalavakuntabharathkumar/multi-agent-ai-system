"""
LangGraph-based execution engine.

Orchestration flow:
  planner ──> worker ──[route_after_worker]──> worker  (retry, up to 3 attempts)
                                           └──> advance ──[route_after_advance]──> worker (next step)
                                                                               └──> END
Dependency-aware routing: a step is only started once all its `depends_on` /
`dependencies` entries are present in `completed_step_ids`.
"""

# Core execution engine: builds and runs a LangGraph state machine that
# drives the planner → worker pipeline with retry logic and dependency ordering.

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
_memory = Memory()           # shared in-memory store for step outputs
_planner = PlannerAgent()    # LLM-powered planner that produces the task plan
_worker = WorkerAgent(_memory)  # executes individual plan steps using tools


# ── Graph state ───────────────────────────────────────────────────────────────
class GraphState(TypedDict):
    """All state carried through the LangGraph execution graph."""
    task: str                          # the original user task string
    plan: Dict[str, Any]               # full plan object returned by the planner
    steps: List[Dict[str, Any]]        # ordered list of steps from the plan
    current_step_index: int            # index of the step currently being executed
    current_attempt: int               # how many times the current step has been tried
    trace: List[Dict[str, Any]]        # history of all step execution results
    completed_step_ids: List[str]      # ids of steps that have finished successfully
    final_output: Dict[str, Any]       # aggregated outputs after all steps complete


# ── Nodes ─────────────────────────────────────────────────────────────────────
def planner_node(state: GraphState) -> Dict[str, Any]:
    """Call the planner to generate a step-by-step plan from the user task."""
    logger.info("planner_node: generating plan")
    plan = _planner.create_plan(state["task"])  # ask LLM to break task into steps
    _memory.set_step_output("user_task", state["task"])  # store raw task for workers to reference
    return {
        "plan": plan,
        "steps": plan.get("steps", []),  # extract the steps list from the plan dict
        "current_step_index": 0,          # start at the first step
        "current_attempt": 0,
        "trace": [],
        "completed_step_ids": [],
        "final_output": {},
    }


def worker_node(state: GraphState) -> Dict[str, Any]:
    """Execute the current step and append its result to the trace."""
    steps = state["steps"]
    idx = state["current_step_index"]
    step = steps[idx]  # select the step at the current index
    attempt = state["current_attempt"] + 1  # increment attempt counter (1-based)

    logger.info(f"worker_node: step {step['id']}, attempt {attempt}")
    start = time.time()
    result = _worker.execute_step(step)  # run the tool for this step
    elapsed = round(time.time() - start, 2)  # measure wall-clock time for this step

    result["attempt"] = attempt
    result["elapsed_seconds"] = elapsed

    return {
        "current_attempt": attempt,
        "trace": state["trace"] + [result],  # append this result to the running trace
    }


def advance_node(state: GraphState) -> Dict[str, Any]:
    """Mark the current step complete and find the next eligible step."""
    steps = state["steps"]
    idx = state["current_step_index"]
    step_id = steps[idx]["id"]
    completed = state["completed_step_ids"] + [step_id]  # add current step to completed set

    # Find the first step whose dependencies are all satisfied
    next_idx = None
    for i, s in enumerate(steps):
        if s["id"] in completed:
            continue  # skip already-completed steps
        deps = s.get("depends_on", s.get("dependencies", [])) or []
        if all(d in completed for d in deps):
            next_idx = i  # this step's dependencies are met — it can run next
            break

    logger.info(
        f"advance_node: completed {step_id}, next_idx={next_idx}, "
        f"completed_so_far={completed}"
    )
    return {
        "current_step_index": next_idx if next_idx is not None else idx,
        "current_attempt": 0,  # reset attempt counter for the next step
        "completed_step_ids": completed,
    }


# ── Routing functions ─────────────────────────────────────────────────────────
def route_after_worker(state: GraphState) -> str:
    """Retry same step (up to 3 attempts) or advance to the next step."""
    last_result = state["trace"][-1]  # inspect the most recent step result
    attempt = state["current_attempt"]
    if last_result["status"] != "success" and attempt < 3:
        logger.info(f"route_after_worker: retrying (attempt {attempt})")
        return "retry"  # send back to worker for another attempt
    return "advance"  # move on regardless of success/failure after 3 tries


def route_after_advance(state: GraphState) -> str:
    """Route to next worker call or END when all steps are complete."""
    completed = state["completed_step_ids"]
    steps = state["steps"]
    remaining = [s for s in steps if s["id"] not in completed]  # steps still to run
    if not remaining:
        logger.info("route_after_advance: all steps complete -> END")
        return "done"  # no more steps — terminate the graph
    logger.info(f"route_after_advance: {len(remaining)} step(s) remaining -> worker")
    return "next"  # more steps remain — go back to the worker


# ── Build and compile the graph ───────────────────────────────────────────────
_builder = StateGraph(GraphState)
_builder.add_node("planner", planner_node)
_builder.add_node("worker", worker_node)
_builder.add_node("advance", advance_node)

_builder.set_entry_point("planner")          # graph always starts at the planner
_builder.add_edge("planner", "worker")       # planner output always goes to worker
_builder.add_conditional_edges(
    "worker",
    route_after_worker,
    {"retry": "worker", "advance": "advance"},  # either retry or move to advance
)
_builder.add_conditional_edges(
    "advance",
    route_after_advance,
    {"done": END, "next": "worker"},  # either end the graph or run the next step
)

execution_graph = _builder.compile()  # compile the state graph into a runnable object


# ── Helpers ───────────────────────────────────────────────────────────────────
def _make_initial_state(task: str) -> Dict[str, Any]:
    """Build the blank initial state dict required to start the graph."""
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
    final_state = execution_graph.invoke(_make_initial_state(user_task))  # run graph to completion
    logger.info("executor.run completed")
    return {
        "task": user_task,
        "plan": final_state["plan"],
        "trace": final_state["trace"],
        "final_output": _memory.get_context(),  # return all stored step outputs
    }


def run_stream(user_task: str) -> Generator[Dict[str, Any], None, None]:
    """Stream graph node outputs as SSE-compatible events."""
    logger.info("executor.run_stream started (LangGraph)")
    for chunk in execution_graph.stream(_make_initial_state(user_task)):
        for node_name, update in chunk.items():
            if node_name == "planner":
                yield {"event": "plan", "data": update.get("plan", {})}  # emit the generated plan
            elif node_name == "worker":
                trace = update.get("trace", [])
                if trace:
                    yield {"event": "step", "data": trace[-1]}  # emit the latest step result
            # advance_node updates are internal routing state — no SSE event
    final_output = _memory.get_context()
    logger.info("executor.run_stream completed")
    yield {"event": "done", "data": final_output}  # signal that all steps are finished


# ── Backward-compatible ExecutionEngine wrapper ───────────────────────────────
class ExecutionEngine:
    """Thin wrapper kept for import compatibility. Delegates to execution_graph."""

    def run(self, user_task: str) -> Dict[str, Any]:
        return run(user_task)

    def run_stream(self, user_task: str) -> Generator[Dict[str, Any], None, None]:
        return run_stream(user_task)
