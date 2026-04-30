from fastapi import APIRouter, Request, UploadFile, File, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import os, hashlib, shutil
from app.config import DOCS_DIR
from app.rag.loaders import load_document
from app.rag.semantic_chunker import SemanticChunker
from app.rag.embeddings import EmbeddingProvider
from app.rag.store import VectorStore

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")

store = VectorStore()
embedder = EmbeddingProvider()
chunker = SemanticChunker(embedder.model)

def file_hash(file_path):
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

@router.get("/", response_class=HTMLResponse)
async def ingest_page(request: Request):
    docs = store.get_all_documents()
    return templates.TemplateResponse("ingest.html", {"request": request, "documents": docs})

@router.post("/", response_class=HTMLResponse)
async def ingest_files(request: Request, files: list[UploadFile] = File(...), force_rebuild: bool = Form(False)):
    for file in files:
        # Save file
        file_path = os.path.join(DOCS_DIR, file.filename)
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Hash check
        fhash = file_hash(file_path)
        if not force_rebuild:
            # Check if already in store (by source_hash)
            existing = store.collection.get(where={"source_hash": fhash}, include=[])
            if existing["ids"]:
                # Already indexed, skip
                os.remove(file_path)
                continue

        # Load, chunk, embed, store
        pages = load_document(file_path)
        chunks = chunker.chunk_pages(pages)
        store.add_chunks(chunks, source_file=file.filename, source_hash=fhash, embedding_provider=embedder)

    # Redirect to GET to show updated list
    return RedirectResponse(url="/ingest", status_code=303)

@router.get("/documents")
def list_documents():
    return store.get_all_documents()

@router.delete("/documents/{file_id}")
def delete_document(file_id: str):
    # file_id could be source_hash; we need to map it properly.
    # For simplicity, we accept source_hash and delete.
    store.delete_by_source_hash(file_id)
    return {"status": "deleted"}

@router.post("/rebuild")
def rebuild():
    # Delete all and reindex all files in data/docs
    store.collection.delete(where={})
    for fname in os.listdir(DOCS_DIR):
        file_path = os.path.join(DOCS_DIR, fname)
        if os.path.isfile(file_path):
            fhash = file_hash(file_path)
            pages = load_document(file_path)
            chunks = chunker.chunk_pages(pages)
            store.add_chunks(chunks, source_file=fname, source_hash=fhash, embedding_provider=embedder)
    return {"status": "rebuilding completed"}