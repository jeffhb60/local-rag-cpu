from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import json
from app.config import SETTINGS_FILE

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

@router.get("/", response_class=HTMLResponse)
async def settings_page(request: Request):
    with open(SETTINGS_FILE, "r") as f:
        settings = json.load(f)
    return templates.TemplateResponse("settings.html", {"request": request, "settings": settings})

@router.post("/", response_class=HTMLResponse)
async def update_settings(request: Request,
                          system_prompt: str = Form(...),
                          rag_prompt_template: str = Form(...),
                          context_template: str = Form(...),
                          top_k: int = Form(...),
                          temperature: float = Form(...),
                          strict_grounding: bool = Form(False),
                          default_provider: str = Form(...),
                          default_model: str = Form(...),
                          mode: str = Form(...)):
    new_settings = {
        "system_prompt": system_prompt,
        "rag_prompt_template": rag_prompt_template,
        "context_template": context_template,
        "top_k": top_k,
        "temperature": temperature,
        "strict_grounding": strict_grounding,
        "default_provider": default_provider,
        "default_model": default_model,
        "mode": mode
    }
    with open(SETTINGS_FILE, "w") as f:
        json.dump(new_settings, f, indent=2)
    return RedirectResponse(url="/settings", status_code=303)