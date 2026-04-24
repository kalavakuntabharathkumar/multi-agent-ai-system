from typing import Any, Dict

class Memory:
    def __init__(self) -> None:
        self.store: Dict[str, Any] = {}

    def set_step_output(self, step_id: str, output: Any) -> None:
        self.store[step_id] = output

    def get_step_output(self, step_id: str) -> Any:
        return self.store.get(step_id)

    def get_context(self) -> Dict[str, Any]:
        return dict(self.store)
