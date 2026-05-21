import re
from pathlib import Path

from fastapi import APIRouter

from app.agents.chat_assistant import chat_assistant_answer
from app.agents.reviser import revise_learning_plan
from app.core.workflow import LearningWorkflow
from app.models.schemas import (
    ChatRequest,
    ChatResponse,
    PlanRequest,
    PlanResponse,
    RevisePlanRequest,
    RevisePlanResponse,
)

router = APIRouter()
workflow = LearningWorkflow()

OUTPUTS_DIR = Path("outputs")
OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)


def _sanitize_filename(goal: str) -> str:
    sanitized = re.sub(r"[\\/:*?\"<>|]+", "", goal)
    sanitized = sanitized.strip().replace(" ", "_")
    if not sanitized:
        sanitized = "learning_plan"
    return f"{sanitized}_plan.md"


def _revised_output_path(output_file: str | None) -> Path:
    if output_file:
        original_name = Path(output_file).name
        original_name = re.sub(r"[\\/:*?\"<>|]+", "", original_name).strip()
        if not original_name:
            original_name = "learning_plan.md"
        original_path = Path(original_name)
        if original_path.suffix:
            stem = original_path.stem
            revised_stem = stem if stem.endswith("_revised") else f"{stem}_revised"
            revised_name = f"{revised_stem}{original_path.suffix}"
        else:
            revised_name = f"{original_path.name}_revised.md"
    else:
        revised_name = "learning_plan_revised.md"

    return OUTPUTS_DIR / revised_name


@router.post("/generate-plan", response_model=PlanResponse)
def generate_plan(request: PlanRequest) -> PlanResponse:
    state = workflow.run(request.goal, request.level, request.duration)
    final_markdown = state.get("final_markdown", "")
    filename = _sanitize_filename(request.goal)
    output_path = OUTPUTS_DIR / filename
    output_path.write_text(final_markdown, encoding="utf-8")

    return PlanResponse(
        planner_result=state.get("planner_result", ""),
        researcher_result=state.get("researcher_result", ""),
        final_markdown=final_markdown,
        output_file=str(output_path).replace("\\", "/"),
    )


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    answer = chat_assistant_answer(request.question, request.context)
    return ChatResponse(answer=answer)


@router.post("/revise-plan", response_model=RevisePlanResponse)
def revise_plan(request: RevisePlanRequest) -> RevisePlanResponse:
    revised_markdown = revise_learning_plan(
        request.current_markdown,
        request.chat_history,
        request.instruction,
    )
    output_path = _revised_output_path(request.output_file)
    output_path.write_text(revised_markdown, encoding="utf-8")

    return RevisePlanResponse(
        revised_markdown=revised_markdown,
        output_file=str(output_path).replace("\\", "/"),
    )
