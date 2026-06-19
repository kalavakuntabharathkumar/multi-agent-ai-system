from typing import Any, Dict
from langchain_core.chat_history import InMemoryChatMessageHistory
from langchain_core.messages import HumanMessage, AIMessage


class Memory:
    def __init__(self) -> None:
        self._history = InMemoryChatMessageHistory()
        self._store: Dict[str, Any] = {}

    def set_step_output(self, step_id: str, output: Any) -> None:
        self._store[step_id] = output
        value = output.get("result", str(output)) if isinstance(output, dict) else str(output)
        self._history.add_messages([
            HumanMessage(content=f"step:{step_id}"),
            AIMessage(content=value),
        ])

    def get_step_output(self, step_id: str) -> Any:
        return self._store.get(step_id)

    def get_context(self) -> Dict[str, Any]:
        return dict(self._store)

    def get_history(self) -> str:
        messages = self._history.messages
        return "\n".join(
            f"{m.type}: {m.content}" for m in messages
        ) if messages else ""
