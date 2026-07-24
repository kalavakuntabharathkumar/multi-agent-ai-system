# In-memory store for step outputs and conversation history.
# Shared across the planner and all worker steps within a single run.

from typing import Any, Dict
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage


class Memory:
    def __init__(self) -> None:
        self._history = InMemoryChatMessageHistory()  # tracks step inputs/outputs as chat messages
        self._store: Dict[str, Any] = {}              # key-value map of step_id → output

    def set_step_output(self, step_id: str, output: Any) -> None:
        """Store a step's output and append it to the chat history."""
        self._store[step_id] = output
        # Extract the result text to log into the conversation history
        value = output.get("result", str(output)) if isinstance(output, dict) else str(output)
        self._history.add_messages([
            HumanMessage(content=f"step:{step_id}"),  # record which step produced this output
            AIMessage(content=value),                  # record the step's text result
        ])

    def get_step_output(self, step_id: str) -> Any:
        """Retrieve the stored output for a given step id, or None if not found."""
        return self._store.get(step_id)

    def get_context(self) -> Dict[str, Any]:
        """Return all stored step outputs as a plain dict (used as the final result)."""
        return dict(self._store)

    def get_history(self) -> str:
        """Return the full conversation history as a newline-joined string."""
        messages = self._history.messages
        return "\n".join(
            f"{m.type}: {m.content}" for m in messages
        ) if messages else ""
