import json
import os
from typing import Any, Dict, List
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from core.logger import get_logger

load_dotenv()
logger = get_logger()

_PLANNER_PROMPT = PromptTemplate(
    input_variables=["task"],
    template=(
        "You are a task planner. Break a complex user request into a sequence of ordered subtasks. "
        "Return only valid JSON with a top-level 'steps' array. Each step must include id, description, tool, and dependencies. "
        "Choose the best tool for each subtask from this list:\n"
        "  - summarize: condense a piece of text into a shorter summary\n"
        "  - linkedin_post: write a professional LinkedIn post from a summary\n"
        "  - email_draft: draft a concise email from a summary\n"
        "  - web_search: search the web for up-to-date information on a topic\n"
        "  - document_qa: answer a question from a provided document or text\n"
        "Dependencies should reference prior step ids. "
        "Input task: {task}"
    ),
)

_planner_chain = None


def _get_planner_chain():
    global _planner_chain
    if _planner_chain is None:
        api_key = os.getenv("OPENAI_API_KEY", "")
        llm = ChatOpenAI(model="gpt-3.5-turbo", temperature=0.3, max_tokens=500, openai_api_key=api_key)
        _planner_chain = _PLANNER_PROMPT | llm | StrOutputParser()
    return _planner_chain


class PlannerAgent:
    def __init__(self) -> None:
        pass

    def create_plan(self, user_task: str) -> Dict[str, Any]:
        logger.info("PlannerAgent creating plan")
        chain = _get_planner_chain()
        raw_text = chain.invoke({"task": user_task}).strip()

        try:
            data = json.loads(raw_text)
            if isinstance(data, dict) and data.get("steps"):
                self._validate_plan(data["steps"])
                logger.info("PlannerAgent generated structured plan")
                return data
        except (json.JSONDecodeError, ValueError):
            logger.warning("Planner returned invalid JSON, using fallback planner")

        return self._fallback_plan(user_task)

    def _validate_plan(self, steps: List[Dict[str, Any]]) -> None:
        valid_tools = {"summarize", "linkedin_post", "email_draft", "web_search", "document_qa"}
        if not steps or not isinstance(steps, list):
            raise ValueError("Planner output must contain a non-empty steps list")
        for step in steps:
            if "id" not in step or "tool" not in step or "description" not in step:
                raise ValueError("Each step must contain id, tool, and description")
            if "dependencies" not in step:
                step["dependencies"] = []
            if step["tool"] not in valid_tools:
                step["tool"] = "summarize"

    def _fallback_plan(self, task: str) -> Dict[str, Any]:
        logger.info("Using fallback planner for task")
        return {
            "task": task,
            "steps": [
                {"id": "step1", "description": "Summarize the user's content.", "tool": "summarize", "dependencies": []},
                {"id": "step2", "description": "Generate a LinkedIn post from the summary.", "tool": "linkedin_post", "dependencies": ["step1"]},
                {"id": "step3", "description": "Draft an email based on the summary.", "tool": "email_draft", "dependencies": ["step1", "step2"]},
            ],
        }
