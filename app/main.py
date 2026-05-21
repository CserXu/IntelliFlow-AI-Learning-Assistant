from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.api.routes import router

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

app = FastAPI(
    title="IntelliFlow AI 智能学习助手",
    description="基于 LangGraph 的多 Agent 学习路线生成系统",
)
app.include_router(router)


@app.get("/", response_class=HTMLResponse)
def root(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "index.html")


@app.get("/result", response_class=HTMLResponse)
def result_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "result.html")
