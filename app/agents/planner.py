from __future__ import annotations

import re

from app.core.llm import OpenAIClient
from app.models.schemas import LearningState


def _parse_duration_weeks(duration: str) -> int:
    match = re.search(r"(\d+)", duration)
    if match:
        return max(1, int(match.group(1)))
    return 2


def _simulate_planner(goal: str, level: str, duration: str) -> str:
    weeks = _parse_duration_weeks(duration)
    stages = []
    stages.append(
        f"阶段 1：基础理解 - 对于目标“{goal}”，从核心概念、环境搭建和最常见术语入手。"
    )
    if weeks > 1:
        stages.append(
            f"阶段 2：进阶实践 - 在第 2 周开始构建小练习项目，掌握典型用例。"
        )
    if weeks > 2:
        stages.append(
            f"阶段 3：综合应用 - 在后续周内整合知识，完成一个更完整的案例。"
        )

    return (
        f"学习目标：{goal}\n"
        f"当前水平：{level}\n"
        f"周期建议：{duration}\n\n"
        "学习阶段拆解：\n"
        + "\n".join(f"- {item}" for item in stages)
        + "\n\n执行步骤：\n"
        "1. 激活学习目标，定义关键结果。\n"
        "2. 结合时间安排制定周计划。\n"
        "3. 固定复盘与练习，确保知识沉淀。\n"
    )


def planner_agent(state: LearningState, llm_client: OpenAIClient | None = None) -> str:
    goal = state.get("goal", "学习目标").strip()
    level = state.get("level", "零基础").strip()
    duration = state.get("duration", "2周").strip()

    if llm_client and llm_client.api_key:
        messages = [
            {
                "role": "system",
                "content": (
                    "你是一个学习规划助手。根据用户的学习目标、基础水平和学习周期，"
                    "拆解合理的学习阶段、模块和执行步骤。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"目标：{goal}\n基础水平：{level}\n周期：{duration}\n"
                    "请生成清晰的阶段划分和执行步骤。"
                ),
            },
        ]
        return llm_client.create_chat_completion(messages)

    return _simulate_planner(goal, level, duration)
