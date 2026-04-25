from pathlib import Path

from docx import Document
from pypdf import PdfReader


SUPPORTED_FILES = {".pdf", ".docx", ".txt", ".md"}


def read_pdf(path: Path) -> list[dict]:
    reader = PdfReader(str(path))
    pieces = []

    for page_number, page in enumerate(reader.pages, start=1):
        text = page.extract_text() or ""
        text = cleanup(text)

        if text:
            pieces.append(
                {
                    "text": text,
                    "page": page_number,
                }
            )

    return pieces


def read_docx(path: Path) -> list[dict]:
    doc = Document(str(path))
    lines = []

    for paragraph in doc.paragraphs:
        text = paragraph.text.strip()
        if text:
            lines.append(text)

    return [{"text": "\n".join(lines), "page": None}]


def read_text(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    return [{"text": cleanup(text), "page": None}]


def cleanup(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def load_file(path: Path) -> list[dict]:
    ext = path.suffix.lower()

    if ext == ".pdf":
        return read_pdf(path)

    if ext == ".docx":
        return read_docx(path)

    if ext in {".txt", ".md"}:
        return read_text(path)

    return []