from typing import Any, Dict
from core.memory import Memory
from core.logger import get_logger
from tools.text_tools import create_text_from_tool

logger = get_logger()

class WorkerAgent:
    def __init__(self, memory: Memory) -> None:
        self.memory = memory

    def _build_input(self, step: Dict[str, Any]) -> Dict[str, str]:
        dependencies = step.get("dependencies", []) or []
        context = {}
        for dep in dependencies:
            output = self.memory.get_step_output(dep)
            if output and isinstance(output, dict):
                context[dep] = output.get("result", "")
        if not context:
            root_task_output = self.memory.get_step_output("user_task")
            if root_task_output:
                context["text"] = root_task_output

        if step.get("tool") == "summarize":
            context["text"] = step.get("source_text", "") or context.get("text", "") or " ".join(str(v) for v in context.values())
        else:
            context["summary"] = step.get("source_text", "") or context.get("text", "") or " ".join(str(v) for v in context.values())
            context["text"] = context["summary"]
        return context

    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        step_id = step.get("id", "unknown")
        tool_name = step.get("tool", "unknown")
        logger.info(f"Worker executing step {step_id} with tool {tool_name}")
        payload = self._build_input(step)

        try:
            result = create_text_from_tool(tool_name, payload)
            status = "success"
            confidence = 0.9
            logger.info(f"Step {step_id} completed successfully")
        except Exception as error:
            result = f"Task failed: {str(error)}"
            status = "failed"
            confidence = 0.3
            logger.error(f"Step {step_id} failed: {error}")

        output = {
            "id": step_id,
            "tool": tool_name,
            "result": result,
            "status": status,
            "confidence": confidence,
        }
        self.memory.set_step_output(step_id, output)
        return output
