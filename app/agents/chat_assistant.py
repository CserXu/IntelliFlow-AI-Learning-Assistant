from __future__ import annotations

import re

from app.core.llm import OpenAIClient
from app.tools.chat_web_search import search_chat_web


MAX_CONTEXT_CHARS = 12000
WEB_SEARCH_ENABLED_PREFIX = "[Web Search Enabled]"
SEARCH_INTENT_KEYWORDS = (
    "网站",
    "网址",
    "链接",
    "视频",
    "教程",
    "课程",
    "最新",
    "推荐",
    "github",
    "git hub",
    "文档",
    "官方",
    "官网",
    "资料",
    "资源",
    "youtube",
    "bilibili",
    "b站",
    "论文",
    "博客",
    "示例",
    "demo",
    "repo",
    "repository",
)


def _trim_context(context: str) -> str:
    context = context.strip()
    if len(context) <= MAX_CONTEXT_CHARS:
        return context
    return context[:MAX_CONTEXT_CHARS].rstrip() + "\n\n[上下文已截断]"


def _extract_keywords(question: str) -> list[str]:
    words = re.findall(r"[\w\u4e00-\u9fff]+", question.lower())
    return [word for word in words if len(word) >= 2][:8]


def _select_relevant_lines(question: str, context: str) -> list[str]:
    keywords = _extract_keywords(question)
    lines = [line.strip() for line in context.splitlines() if line.strip()]
    if not keywords:
        return lines[:8]

    matched: list[str] = []
    for line in lines:
        lowered = line.lower()
        if any(keyword in lowered for keyword in keywords):
            matched.append(line)
        if len(matched) >= 8:
            break

    return matched or lines[:8]


def _fallback_answer(question: str, context: str) -> str:
    relevant_lines = _select_relevant_lines(question, context)
    if not context.strip():
        return "我还没有拿到当前学习路线内容。请先生成学习路线，再围绕路线继续提问。"

    quoted_plan = "\n".join(f"- {line}" for line in relevant_lines)
    return (
        "基于当前学习路线，我建议这样处理：\n\n"
        f"{quoted_plan}\n\n"
        f"针对你的问题“{question}”，优先回到路线中的阶段目标和实践任务来安排：先确认当前阶段，"
        "再选择一个最小练习任务完成验证，最后把遇到的问题记录到复盘重点里。"
    )


def _needs_web_search(question: str) -> bool:
    lowered = question.lower()
    return any(keyword in lowered for keyword in SEARCH_INTENT_KEYWORDS)


def _build_search_query(question: str, context: str) -> str:
    plan_keywords = _select_relevant_lines(question, context)[:3]
    plan_hint = " ".join(line[:120] for line in plan_keywords)
    return f"{question} {plan_hint}".strip()


def _extract_urls(text: str) -> list[str]:
    urls = re.findall(r"https?://[^\s)）]+", text)
    deduped: list[str] = []
    for url in urls:
        cleaned = url.rstrip(".,;。；")
        if cleaned not in deduped:
            deduped.append(cleaned)
    return deduped


def _ensure_urls_in_answer(answer: str, search_text: str) -> str:
    if re.search(r"https?://", answer):
        return answer

    urls = _extract_urls(search_text)
    if not urls:
        return answer

    link_lines = "\n".join(f"- {url}" for url in urls[:6])
    return f"{answer.rstrip()}\n\n搜索结果链接：\n{link_lines}"


def _answer_with_search(
    question: str,
    context: str,
    search_text: str,
    client: OpenAIClient,
) -> str:
    if client.api_key:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 IntelliFlow 的学习问答 Chat Assistant，具备 Web Search 结果整理能力。"
                    "回答必须结合当前学习路线 context 和 Web Search 结果。"
                    "优先提供真实 URL；如果搜索结果中包含 YouTube、Bilibili、GitHub、官方文档或课程链接，"
                    "请按类别列出。不要编造搜索结果中不存在的网址。回答使用中文，简洁、可执行。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"当前学习路线 context：\n{context}\n\n"
                    f"用户问题：\n{question}\n\n"
                    f"Web Search 结果：\n{search_text}\n\n"
                    "请基于学习路线和真实搜索结果回答。输出建议包含：推荐链接、适合的学习顺序、注意事项。"
                ),
            },
        ]
        answer = client.create_chat_completion(messages, temperature=0.25)
        return _ensure_urls_in_answer(answer, search_text)

    return (
        "我根据当前学习路线检索到这些网页结果，你可以优先查看：\n\n"
        f"{search_text}\n\n"
        "建议先选择官方文档或高质量课程建立基础，再用视频教程跟做一个小练习。"
    )


def _answer_without_search(question: str, context: str, client: OpenAIClient) -> str:
    if client.api_key:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是 IntelliFlow 的学习问答 Chat Assistant。"
                    "回答必须紧密结合用户提供的当前学习路线 context。"
                    "不要脱离学习计划泛泛而谈；如果问题超出 context，请先说明当前路线中缺少该信息，"
                    "再给出如何把它纳入学习计划的建议。回答使用中文，结构清晰、可执行。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"当前学习路线 context：\n{context}\n\n"
                    f"用户问题：\n{question}\n\n"
                    "请基于上述 context 回答。"
                ),
            },
        ]
        return client.create_chat_completion(messages, temperature=0.3)

    return _fallback_answer(question, context)


def chat_assistant_answer(
    question: str,
    context: str,
    llm_client: OpenAIClient | None = None,
) -> str:
    question = question.strip()
    context = _trim_context(context)

    if not question:
        return "请先输入一个具体问题。"

    if not context:
        return "我还没有拿到当前学习路线内容。请先生成学习路线，再围绕路线继续提问。"

    client = llm_client or OpenAIClient()

    if _needs_web_search(question):
        search_query = _build_search_query(question, context)
        search_text = search_chat_web(search_query)
        if not search_text.startswith("[Chat Web Search Fallback]"):
            answer = _answer_with_search(question, context, search_text, client)
            return f"{WEB_SEARCH_ENABLED_PREFIX}\n{answer}"

    return _answer_without_search(question, context, client)
