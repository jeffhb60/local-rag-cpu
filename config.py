import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DOCS_DIR = BASE_DIR / "docs"
DB_DIR = BASE_DIR / "chroma_db"

COLLECTION = "manuals"

# Use os.getenv to allow easy overrides without touching the code
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = os.getenv("CHAT_MODEL", "llama3.2:3b")
EMBED_MODEL = os.getenv("EMBED_MODEL", "all-minilm")

CHUNK_CHARS = int(os.getenv("CHUNK_CHARS", 1000))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", 180))

EMBED_BATCH_SIZE = int(os.getenv("EMBED_BATCH_SIZE", 16))
TOP_K = int(os.getenv("TOP_K", 5))

# Centralized timeouts
GENERATE_TIMEOUT = int(os.getenv("GENERATE_TIMEOUT", 300))
EMBED_TIMEOUT = int(os.getenv("EMBED_TIMEOUT", 180))