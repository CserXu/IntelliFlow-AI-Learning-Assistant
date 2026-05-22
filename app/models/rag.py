from __future__ import annotations

from pydantic import BaseModel, Field


class RagUploadResponse(BaseModel):
    filename: str
    chunks_added: int
    message: str


class RagQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RagSource(BaseModel):
    filename: str
    chunk_id: str
    content_preview: str


class RagQueryResponse(BaseModel):
    answer: str
    sources: list[RagSource]


class RagRevisePlanRequest(BaseModel):
    original_plan: str = Field(..., min_length=1)
    instruction: str = Field(..., min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class RagRevisePlanResponse(BaseModel):
    revised_plan: str
    sources: list[RagSource]
