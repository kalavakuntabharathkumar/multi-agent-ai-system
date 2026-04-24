from pathlib import Path
from typing import Optional


def save_text_file(path: str, content: str) -> str:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
    return str(file_path)


def load_text_file(path: str) -> Optional[str]:
    file_path = Path(path)
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return None
