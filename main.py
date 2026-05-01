from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from api.routes import router as api_router
from config import settings


app = FastAPI(title=settings.app_name)

app.mount("/static", StaticFiles(directory="static"), name="static")

templates = Jinja2Templates(directory="templates")

app.include_router(api_router, prefix="/api")


@app.get("/")
async def root():
    return RedirectResponse(url="/upload")


@app.get("/upload")
async def upload_page(request: Request):
    return templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "settings": settings,
            "active_page": "upload",
        },
    )


@app.get("/reindex")
async def reindex_page(request: Request):
    return templates.TemplateResponse(
        "reindex.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "settings": settings,
            "active_page": "reindex",
        },
    )


@app.get("/evaluation")
async def evaluation_page(request: Request):
    return templates.TemplateResponse(
        "evaluation.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "settings": settings,
            "active_page": "evaluation",
        },
    )


@app.get("/chat")
async def chat_page(request: Request):
    return templates.TemplateResponse(
        "chat.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "settings": settings,
            "active_page": "chat",
        },
    )