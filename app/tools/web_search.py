from __future__ import annotations

import os
from pprint import pformat
from typing import Any

from dotenv import load_dotenv
from tavily import TavilyClient
from tavily.errors import InvalidAPIKeyError, MissingAPIKeyError, UsageLimitExceededError

load_dotenv()


def search_web(query: str) -> str:
    """Search the web using Tavily and return a text summary of the results."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        print("[TAVILY ERROR] Missing API Key", flush=True)
        return _fallback_search(query, "未配置 Tavily API Key")

    try:
        client = TavilyClient(api_key=api_key)
        response = client.search(
            query=query,
            max_results=5,
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
    if not results:
        return _fallback_search(query, "未返回有效搜索结果")

    lines = [f"Web Search 结果（{query}）："]
    for index, item in enumerate(results[:5], start=1):
        title = item.get("title") or item.get("headline") or item.get("name") or "搜索结果"
        url = item.get("url") or item.get("link") or ""
        snippet = item.get("answer") or item.get("snippet") or item.get("summary") or item.get("text") or ""
        lines.append(f"{index}. {title}")
        if url:
            lines.append(f"   链接：{url}")
        if snippet:
            lines.append(f"   摘要：{snippet}")
    return "\n".join(lines)


def _fallback_search(query: str, reason: str) -> str:
    return (
        f"[Web Search Fallback] 无法执行 Tavily 搜索：{reason}。\n"
        f"请使用模拟资料输出。\n"
        "推荐资料类型：\n"
        "- 官方文档与入门指南\n"
        "- 教程视频与实战博客\n"
        "- 代码示例与小项目实践\n\n"
        "官方文档方向：\n"
        f"- 阅读与理解与目标相关的核心官方文档，结合最新版本进行实践。\n\n"
        "实践项目方向：\n"
        "- 搭建一个简单的练习项目，逐步实现关键功能。\n"
        "- 通过小项目理解常见使用场景和性能优化点。\n\n"
        "复习重点：\n"
        "- 核心概念与术语。\n"
        "- 典型命令或 API 调用。\n"
        "- 实战过程中的常见错误与调试思路。"
    )
