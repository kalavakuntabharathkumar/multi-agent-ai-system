# Web search tool: wraps DuckDuckGo search via LangChain for privacy-friendly queries.
# Uses a lazy singleton so the search tool is only initialized on first call.

import warnings
warnings.filterwarnings("ignore")  # suppress noisy deprecation warnings from langchain_community

from langchain_community.tools import DuckDuckGoSearchRun

_search_tool = None  # lazily initialized singleton — avoids startup overhead


def _get_search_tool() -> DuckDuckGoSearchRun:
    """Return the shared DuckDuckGoSearchRun instance, creating it on first call."""
    global _search_tool
    if _search_tool is None:
        _search_tool = DuckDuckGoSearchRun()
    return _search_tool


def run_web_search(query: str) -> str:
    """Run a DuckDuckGo search and return the result string, or an error message on failure."""
    tool = _get_search_tool()
    try:
        result = tool.run(query)
        return result if result else "No results found."  # guard against empty responses
    except Exception as exc:
        return f"Web search failed: {exc}"
