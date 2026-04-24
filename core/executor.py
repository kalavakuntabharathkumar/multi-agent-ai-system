import time
from typing import Any, Dict, List
from agents.planner import PlannerAgent
from agents.worker import WorkerAgent
from core.memory import Memory
from core.logger import get_logger

logger = get_logger()

class ExecutionEngine:
    def __init__(self) -> None:
        self.memory = Memory()
        self.planner = PlannerAgent()
        self.worker = WorkerAgent(self.memory)

    def run(self, user_task: str) -> Dict[str, Any]:
        logger.info("ExecutionEngine started")
        plan = self.planner.create_plan(user_task)
        self.memory.set_step_output("user_task", user_task)
        steps = plan.get("steps", [])
        trace: List[Dict[str, Any]] = []

        for step in steps:
            step_id = step["id"]
            attempt = 0
            step_output: Dict[str, Any] = {"id": step_id, "status": "pending"}

            while attempt <= 2:
                attempt += 1
                logger.info(f"Executing {step_id}, attempt {attempt}")
                start = time.time()
                result = self.worker.execute_step(step)
                elapsed = time.time() - start

                result["attempt"] = attempt
                result["elapsed_seconds"] = round(elapsed, 2)
                trace.append(result)

                if result["status"] == "success":
                    logger.info(f"Step {step_id} succeeded on attempt {attempt}")
                    break
                if attempt == 3:
                    logger.error(f"Step {step_id} failed after 3 attempts")
                    break
                logger.warning(f"Retrying step {step_id}")

        final_output = self.memory.get_context()
        logger.info("ExecutionEngine completed")
        return {
            "task": user_task,
            "plan": plan,
            "trace": trace,
            "final_output": final_output,
        }
