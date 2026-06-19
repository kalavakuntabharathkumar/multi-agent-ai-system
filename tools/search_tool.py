import warnings
warnings.filterwarnings("ignore")

from langchain_community.tools import DuckDuckGoSearchRun

_search_tool = None


def _get_search_tool() -> DuckDuckGoSearchRun:
    global _search_tool
    if _search_tool is None:
        _search_tool = DuckDuckGoSearchRun()
    return _search_tool


def run_web_search(query: str) -> str:
    tool = _get_search_tool()
    try:
        result = tool.run(query)
        return result if result else "No results found."
    except Exception as exc:
        return f"Web search failed: {exc}"
