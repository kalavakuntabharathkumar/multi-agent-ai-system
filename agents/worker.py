# WorkerAgent: executes a single plan step by dispatching to the correct tool.
# Reads inputs from shared Memory and writes the step output back to Memory.

from typing import Any, Dict
from core.memory import Memory
from core.logger import get_logger
from tools.text_tools import create_text_from_tool

logger = get_logger()


class WorkerAgent:
    def __init__(self, memory: Memory) -> None:
        self.memory = memory  # shared memory store used to pass outputs between steps

    def _build_input(self, step: Dict[str, Any]) -> Dict[str, str]:
        """Assemble the tool's input dict by pulling outputs of dependency steps from memory."""
        dependencies = step.get("dependencies", []) or []
        context = {}
        for dep in dependencies:
            output = self.memory.get_step_output(dep)  # retrieve this dependency's result
            if output and isinstance(output, dict):
                context[dep] = output.get("result", "")  # extract the text result

        if not context:
            # No dependency outputs found — fall back to the original user task text
            root_task_output = self.memory.get_step_output("user_task")
            if root_task_output:
                context["text"] = root_task_output

        # Shape the context keys to match what each tool type expects
        if step.get("tool") == "summarize":
            context["text"] = step.get("source_text", "") or context.get("text", "") or " ".join(str(v) for v in context.values())
        else:
            # Non-summarize tools expect a "summary" key as their primary input
            context["summary"] = step.get("source_text", "") or context.get("text", "") or " ".join(str(v) for v in context.values())
            context["text"] = context["summary"]
        return context

    def execute_step(self, step: Dict[str, Any]) -> Dict[str, Any]:
        """Run one plan step, store its output in memory, and return a result dict."""
        step_id = step.get("id", "unknown")
        tool_name = step.get("tool", "unknown")
        logger.info(f"Worker executing step {step_id} with tool {tool_name}")
        payload = self._build_input(step)  # gather inputs for this step from memory

        try:
            result = create_text_from_tool(tool_name, payload)  # dispatch to the matching tool
            status = "success"
            confidence = 0.9
            logger.info(f"Step {step_id} completed successfully")
        except Exception as error:
            result = f"Task failed: {str(error)}"
            status = "failed"
            confidence = 0.3  # low confidence score on failure
            logger.error(f"Step {step_id} failed: {error}")

        output = {
            "id": step_id,
            "tool": tool_name,
            "result": result,
            "status": status,
            "confidence": confidence,
        }
        self.memory.set_step_output(step_id, output)  # persist result for downstream steps
        return output
