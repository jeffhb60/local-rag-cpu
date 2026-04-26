import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent

# Load .env from the same folder as config.py
load_dotenv(BASE_DIR / ".env")


def get_path_env(name: str, default: Path) -> Path:
    value = os.getenv(name)

    if not value:
        return default

    path = Path(value)

    if path.is_absolute():
        return path

    return BASE_DIR / path


def get_int_env(name: str, default: int) -> int:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return int(value)


def get_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)

    if value is None or value.strip() == "":
        return default

    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def get_str_env(name: str, default: str) -> str:
    value = os.getenv(name)

    if value is None:
        return default

    return value.strip()


# Folders
DOCS_DIR = get_path_env("DOCS_DIR", BASE_DIR / "docs")
DB_DIR = get_path_env("DB_DIR", BASE_DIR / "chroma_db")

# ChromaDB
COLLECTION = get_str_env("COLLECTION", "manuals")
INDEX_VERSION = get_str_env("INDEX_VERSION", "ocr-v1")

# Ollama
OLLAMA_URL = get_str_env("OLLAMA_URL", "http://localhost:11434")
CHAT_MODEL = get_str_env("CHAT_MODEL", "llama3.2:3b")
EMBED_MODEL = get_str_env("EMBED_MODEL", "all-minilm")

# Chunking
CHUNK_CHARS = get_int_env("CHUNK_CHARS", 1000)
CHUNK_OVERLAP = get_int_env("CHUNK_OVERLAP", 180)

# Ingestion / retrieval
EMBED_BATCH_SIZE = get_int_env("EMBED_BATCH_SIZE", 16)
TOP_K = get_int_env("TOP_K", 5)

# Timeouts
GENERATE_TIMEOUT = get_int_env("GENERATE_TIMEOUT", 300)
EMBED_TIMEOUT = get_int_env("EMBED_TIMEOUT", 180)

# OCR
OCR_ENABLED = get_bool_env("OCR_ENABLED", True)
OCR_MIN_TEXT_CHARS = get_int_env("OCR_MIN_TEXT_CHARS", 40)
OCR_DPI = get_int_env("OCR_DPI", 200)
OCR_LANG = get_str_env("OCR_LANG", "eng")
TESSERACT_CMD = get_str_env(
    "TESSERACT_CMD",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)