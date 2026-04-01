from __future__ import annotations

import os
from typing import List, Dict

from langchain_community.tools import TavilySearchResults

from config import get_settings


class TavilySearchService:
    def __init__(self) -> None:
        self.settings = get_settings()
        if self.settings.tavily_api_key:
            os.environ["TAVILY_API_KEY"] = self.settings.tavily_api_key

    def is_available(self) -> bool:
        return bool(self.settings.tavily_api_key)

    def search(self, query: str, max_results: int = 3) -> List[Dict]:
        if not query or not self.is_available():
            return []
        try:
            tool = TavilySearchResults(max_results=max_results)
            results = tool.invoke(query)
            return results if isinstance(results, list) else []
        except Exception:
            return []

    def format_results(self, results: List[Dict]) -> str:
        if not results:
            return "외부 검색 결과 없음"

        lines = []
        for idx, item in enumerate(results, start=1):
            title = item.get("title") or item.get("url") or f"result-{idx}"
            content = item.get("content", "")
            url = item.get("url", "")
            lines.append(f"[{idx}] {title}\n- 요약: {content}\n- 출처: {url}")
        return "\n\n".join(lines)
