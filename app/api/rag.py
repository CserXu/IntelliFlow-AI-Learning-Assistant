from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.models.rag import (
    RagQueryRequest,
    RagQueryResponse,
    RagRevisePlanRequest,
    RagRevisePlanResponse,
    RagUploadResponse,
)
from app.services.document_loader import DocumentLoader
from app.services.rag_service import RagService


router = APIRouter(prefix="/api/rag", tags=["rag"])


@router.post("/upload", response_model=RagUploadResponse)
async def upload_document(file: UploadFile = File(...)) -> RagUploadResponse:
    loader = DocumentLoader()
    try:
        saved_path = await loader.save_upload(file)
        service = RagService(document_loader=loader)
        chunks_added = service.ingest_file(saved_path, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to ingest document: {exc}") from exc

    return RagUploadResponse(
        filename=file.filename or saved_path.name,
        chunks_added=chunks_added,
        message="Document uploaded and indexed successfully.",
    )


@router.post("/query", response_model=RagQueryResponse)
def query_knowledge_base(request: RagQueryRequest) -> RagQueryResponse:
    try:
        answer, sources = RagService().answer_question(request.question, request.top_k)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to query knowledge base: {exc}") from exc

    return RagQueryResponse(answer=answer, sources=sources)


@router.post("/revise-plan-with-knowledge", response_model=RagRevisePlanResponse)
def revise_plan_with_knowledge(request: RagRevisePlanRequest) -> RagRevisePlanResponse:
    try:
        revised_plan, sources = RagService().revise_plan_with_knowledge(
            request.original_plan,
            request.instruction,
            request.top_k,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to revise plan with knowledge base: {exc}") from exc

    return RagRevisePlanResponse(revised_plan=revised_plan, sources=sources)
