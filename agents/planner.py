import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
import openai
from core.logger import get_logger

load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")
logger = get_logger()

STEP_TEMPLATE = {
    "id": "",
    "description": "",
    "tool": "",
    "dependencies": [],
}

class PlannerAgent:
    def __init__(self) -> None:
        pass

    def _build_prompt(self, task: str) -> str:
        return (
            "You are a task planner. Break a complex user request into a sequence of ordered subtasks. "
            "Return only valid JSON. Each step must include id, description, tool, and dependencies. "
            "Tool values should be one of: summarize, linkedin_post, email_draft. "
            "Dependencies should reference prior step ids. "
            f"Input task: {task}"
        )

    def create_plan(self, user_task: str) -> Dict[str, Any]:
        logger.info("PlannerAgent creating plan")
        prompt = self._build_prompt(user_task)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
            max_tokens=400,
        )
        raw_text = response.choices[0].message.content.strip()

        try:
            data = json.loads(raw_text)
            if isinstance(data, dict) and data.get("steps"):
                self._validate_plan(data["steps"])
                logger.info("PlannerAgent generated structured plan")
                return data
        except json.JSONDecodeError:
            logger.warning("Planner returned invalid JSON, using fallback planner")

        return self._fallback_plan(user_task)

    def _validate_plan(self, steps: List[Dict[str, Any]]) -> None:
        if not steps or not isinstance(steps, list):
            raise ValueError("Planner output must contain a non-empty steps list")
        for step in steps:
            if "id" not in step or "tool" not in step or "description" not in step:
                raise ValueError("Each step must contain id, tool, and description")
            if "dependencies" not in step:
                step["dependencies"] = []

    def _fallback_plan(self, task: str) -> Dict[str, Any]:
        logger.info("Using fallback planner for task")
        return {
            "task": task,
            "steps": [
                {"id": "step1", "description": "Summarize the user's content.", "tool": "summarize", "dependencies": []},
                {"id": "step2", "description": "Generate a LinkedIn post from the summary.", "tool": "linkedin_post", "dependencies": ["step1"]},
                {"id": "step3", "description": "Draft an email based on the summary and LinkedIn post.", "tool": "email_draft", "dependencies": ["step1", "step2"]},
            ],
        }
