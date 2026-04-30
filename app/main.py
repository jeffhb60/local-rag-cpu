from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import os
from app.routes import ingest, chat, settings, eval

import os
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

import warnings
warnings.filterwarnings("ignore", message=".*ARC4 has been moved.*")
app = FastAPI(title="RAG Project")
templates = Jinja2Templates(directory="app/templates")

# Ensure data directories exist
os.makedirs("data/docs", exist_ok=True)
os.makedirs("data/chroma", exist_ok=True)
if not os.path.exists("data/settings_default.json"):
    import shutil
    shutil.copy("data/settings_default.json", "data/settings_default.json")  # you'd better provide default

# Include routers
app.include_router(ingest.router, prefix="/ingest", tags=["ingest"])
app.include_router(chat.router, prefix="/chat", tags=["chat"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(eval.router, prefix="/eval", tags=["eval"])

@app.get("/")
def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})