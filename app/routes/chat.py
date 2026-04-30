from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from app.rag.pipeline import RAGPipeline

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
pipeline = RAGPipeline()

@router.get("/", response_class=HTMLResponse)
async def chat_page(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request, "answer": None})

@router.post("/", response_class=HTMLResponse)
async def chat(request: Request,
               question: str = Form(...),
               provider: str = Form("ollama"),
               model: str = Form("llama3.1"),
               top_k: int = Form(5),
               temperature: float = Form(0.2),
               mode: str = Form("strict")):
    result = pipeline.answer(
        question=question,
        provider_name=provider,
        model_name=model,
        top_k=top_k,
        temperature=temperature,
        mode=mode
    )
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "question": question,
        "answer": result["answer"],
        "sources": result["sources"]
    })