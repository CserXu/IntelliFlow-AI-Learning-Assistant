from __future__ import annotations

from app.models.schemas import LearningState


def writer_agent(state: LearningState) -> str:
    goal = state.get("goal", "学习目标").strip()
    level = state.get("level", "零基础").strip()
    duration = state.get("duration", "2周").strip()
    planner_result = state.get("planner_result", "").strip()
    researcher_result = state.get("researcher_result", "").strip()

    return (
        f"# 学习路线：{goal}\n\n"
        f"## 目标说明\n"
        f"- 学习目标：{goal}\n"
        f"- 当前水平：{level}\n"
        f"- 推荐周期：{duration}\n\n"
        "## 阶段划分\n"
        f"{planner_result}\n\n"
        "## 推荐资料与研究方向\n"
        f"{researcher_result}\n\n"
        "## 每周/每日任务建议\n"
        "- 结合阶段分解，按周安排小目标。\n"
        "- 每日保持阅读、实践、复盘。\n\n"
        "## 实践项目建议\n"
        "- 构建一个小型项目，巩固核心流程。\n\n"
        "## 复习重点\n"
        "- 循环回顾关键概念与实战经验。\n"
    )
