from __future__ import annotations

import re

from app.core.llm import OpenAIClient
from app.models.schemas import LearningState
from app.tools.web_search import search_web


def _simulate_researcher(planner_text: str) -> str:
    return (
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


def _extract_topic(planner_text: str) -> str:
    match = re.search(r"学习目标[：:]\s*(.+)", planner_text)
    if match:
        return match.group(1).strip()

    # fallback to first line or short summary
    first_line = planner_text.splitlines()[0] if planner_text else ""
    return first_line.strip() or "学习目标"


def _build_research_summary(planner_text: str, search_text: str, llm_client: OpenAIClient | None) -> str:
    if search_text.startswith("[Web Search Fallback]"):
        return _simulate_researcher(planner_text)

    if llm_client and llm_client.api_key:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个智能研究员。根据学习规划和网页搜索结果，整理推荐资料类型、官方文档方向、实践项目方向和复习重点。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"学习规划：\n{planner_text}\n\n网页搜索结果：\n{search_text}\n\n"
                    "请总结推荐资料、官方文档方向、实践项目方向和复习重点。"
                ),
            },
        ]
        return llm_client.create_chat_completion(messages)

    return (
        "搜索结果总结：\n"
        f"{search_text}\n\n"
        "推荐资料类型：\n"
        "- 官方文档与入门指南\n"
        "- 教程视频与实战博客\n"
        "- 代码示例与小项目实践\n\n"
        "官方文档方向：\n"
        "- 阅读与理解与目标相关的核心官方文档，结合最新版本进行实践。\n\n"
        "实践项目方向：\n"
        "- 基于搜索结果中的相关链接，选择最新、权威的项目进行练习。\n"
        "- 将搜索到的实战案例作为学习参考。\n\n"
        "复习重点：\n"
        "- 核心概念与术语。\n"
        "- 典型命令或 API 调用。\n"
        "- 实战过程中的常见错误与调试思路。"
    )


def researcher_agent(state: LearningState, llm_client: OpenAIClient | None = None) -> str:
    planner_result = state.get("planner_result", "").strip()
    topic = _extract_topic(planner_result)
    search_text = search_web(topic)
    return _build_research_summary(planner_result, search_text, llm_client)
