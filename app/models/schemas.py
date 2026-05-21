from __future__ import annotations

from typing_extensions import TypedDict

from pydantic import BaseModel


class PlanRequest(BaseModel):
    goal: str
    level: str
    duration: str


class PlanResponse(BaseModel):
    planner_result: str
    researcher_result: str
    final_markdown: str
    output_file: str


class ChatRequest(BaseModel):
    question: str
    context: str


class ChatResponse(BaseModel):
    answer: str


class ChatMessage(BaseModel):
    role: str
    content: str


class RevisePlanRequest(BaseModel):
    current_markdown: str
    chat_history: list[ChatMessage]
    instruction: str
    output_file: str | None = None


class RevisePlanResponse(BaseModel):
    revised_markdown: str
    output_file: str


class LearningState(TypedDict, total=False):
    goal: str
    level: str
    duration: str
    planner_result: str
    researcher_result: str
    final_markdown: str
