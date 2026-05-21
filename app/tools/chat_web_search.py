from __future__ import annotations

import os
from pprint import pformat
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient
from tavily.errors import InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError

load_dotenv()


def search_chat_web(query: str) -> str:
    """Search web resources for Chat Assistant questions and return link-focused results."""
    query = query.strip()
    if not query:
        return _fallback_search("空搜索问题", "搜索问题为空")

    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("[TAVILY ERROR] Missing API Key", flush=True)
        return _fallback_search(query, "未配置 Tavily API Key")

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=8,
            include_answer="basic",
            include_raw_content="text",
            timeout=30,
        )
        print(
            f"[TAVILY SEARCH]\nquery={query}\nresponse={pformat(response)}",
            flush=True,
        )
        return _format_search_results(query, response)
    except (MissingAPIKeyError, InvalidAPIKeyError, UsageLimitExceededError, Exception) as exc:
        print(f"[TAVILY ERROR] {exc}", flush=True)
        return _fallback_search(query, str(exc))


def _format_search_results(query: str, response: dict[str, Any]) -> str:
    results = response.get("results") or []
    answer = response.get("answer") or ""
    if not results:
        return _fallback_search(query, "未返回有效搜索结果")

    lines = [f"Chat Web Search 结果（{query}）："]
    if answer:
        lines.append(f"搜索摘要：{answer}")

    for index, item in enumerate(results[:8], start=1):
        title = item.get("title") or item.get("headline") or item.get("name") or "搜索结果"
        url = item.get("url") or item.get("link") or ""
        snippet = (
            item.get("content")
            or item.get("answer")
            or item.get("snippet")
            or item.get("summary")
            or item.get("text")
            or ""
        )

        lines.append(f"{index}. {title}")
        if url:
            lines.append(f"   URL: {url}")
        if snippet:
            lines.append(f"   摘要: {snippet[:500]}")

    return "\n".join(lines)


def _fallback_search(query: str, reason: str) -> str:
    return (
        f"[Chat Web Search Fallback] 无法执行 Tavily 搜索：{reason}。\n"
        f"搜索问题：{query}"
    )
