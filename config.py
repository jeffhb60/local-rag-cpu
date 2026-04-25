from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DOCS_DIR = BASE_DIR / "docs"
DB_DIR = BASE_DIR / "chroma_db"

COLLECTION = "manuals"

OLLAMA_URL = "http://localhost:11434"
CHAT_MODEL = "llama3.2:3b"
EMBED_MODEL = "all-minilm"

CHUNK_CHARS = 1000
CHUNK_OVERLAP = 180

EMBED_BATCH_SIZE = 16
TOP_K = 5