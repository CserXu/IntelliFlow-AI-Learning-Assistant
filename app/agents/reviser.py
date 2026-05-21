from __future__ import annotations

import re

from app.core.llm import OpenAIClient
from app.models.schemas import ChatMessage


MAX_MARKDOWN_CHARS = 18000
MAX_HISTORY_CHARS = 12000


def _trim_text(text: str, limit: int) -> str:
    text = text.strip()
    if len(text) <= limit:
        return text
    return text[:limit].rstrip() + "\n\n[内容已截断]"


def _format_chat_history(chat_history: list[ChatMessage]) -> str:
    lines: list[str] = []
    for item in chat_history:
        role = item.role.strip() or "message"
        content = item.content.strip()
        if content:
            lines.append(f"{role}: {content}")
    return _trim_text("\n\n".join(lines), MAX_HISTORY_CHARS)


def _extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)）]+", text)
    deduped: list[str] = []
    for url in urls:
        cleaned = url.rstrip(".,;。；")
        if cleaned not in deduped:
            deduped.append(cleaned)
    return deduped


def _extract_valuable_lines(chat_history_text: str) -> list[str]:
    keywords = (
        "http://",
        "https://",
        "推荐",
        "课程",
        "视频",
        "教程",
        "文档",
        "github",
        "项目",
        "练习",
        "建议",
        "资源",
        "official",
        "youtube",
        "bilibili",
    )
    lines: list[str] = []
    for raw_line in chat_history_text.splitlines():
        line = raw_line.strip("-• \t")
        if not line:
            continue
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords) and line not in lines:
            lines.append(line)
        if len(lines) >= 16:
            break
    return lines


def _fallback_revise(current_markdown: str, chat_history_text: str, instruction: str) -> str:
    urls = _extract_urls(chat_history_text)
    valuable_lines = _extract_valuable_lines(chat_history_text)

    additions: list[str] = []
    if instruction.strip():
        additions.append(f"修订要求：{instruction.strip()}")
    if urls:
        additions.append("补充链接：")
        additions.extend(f"- {url}" for url in urls[:12])
    if valuable_lines:
        additions.append("补充资料与学习建议：")
        additions.extend(f"- {line}" for line in valuable_lines[:12] if line not in urls)

    if not additions:
        additions.append("暂无可提取的新增资料。建议继续在 Chat Assistant 中补充具体链接、课程或项目建议后再更新路线。")

    existing_urls = set(_extract_urls(current_markdown))
    filtered_additions: list[str] = []
    for line in additions:
        line_urls = _extract_urls(line)
        if line_urls and all(url in existing_urls for url in line_urls):
            continue
        if line not in filtered_additions:
            filtered_additions.append(line)

    section = "\n".join(filtered_additions)
    return (
        current_markdown.rstrip()
        + "\n\n## 补充资料与路线调整\n\n"
        + section
        + "\n"
    )


def revise_learning_plan(
    current_markdown: str,
    chat_history: list[ChatMessage],
    instruction: str,
    llm_client: OpenAIClient | None = None,
) -> str:
    current_markdown = _trim_text(current_markdown, MAX_MARKDOWN_CHARS)
    chat_history_text = _format_chat_history(chat_history)
    instruction = instruction.strip()

    if not current_markdown:
        return "请先生成学习路线。"

    client = llm_client or OpenAIClient()
    if client.api_key and chat_history_text:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 IntelliFlow 的 Reviser Agent，负责根据聊天记录修订学习路线 Markdown。"
                    "你需要提取聊天中有价值的补充资料、真实网址、课程链接、项目建议和学习建议，"
                    "将它们整合进原学习路线的合适位置。必须保持 Markdown 结构清晰。"
                    "不要简单追加聊天记录，不要删除原有核心计划，避免重复内容。"
                    "如果聊天中的信息不足，只做最小必要修订。只输出修订后的 Markdown。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"当前学习路线 Markdown：\n{current_markdown}\n\n"
                    f"聊天记录：\n{chat_history_text}\n\n"
                    f"用户修订要求：\n{instruction or '请把聊天中的有效补充资料整合进学习路线。'}\n\n"
                    "请输出完整的 revised Markdown。"
                ),
            },
        ]
        revised = client.create_chat_completion(messages, temperature=0.25).strip()
        if revised:
            return revised

    return _fallback_revise(current_markdown, chat_history_text, instruction)
