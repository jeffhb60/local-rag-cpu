from pathlib import Path

from docx import Document
from pypdf import PdfReader

from config import (
    OCR_ENABLED,
    OCR_MIN_TEXT_CHARS,
    OCR_DPI,
    OCR_LANG,
    TESSERACT_CMD,
)


SUPPORTED_FILES = {".pdf", ".docx", ".txt", ".md"}


def cleanup(text: str) -> str:
    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    return "\n".join(lines)


def setup_tesseract() -> None:
    if not TESSERACT_CMD:
        return

    try:
        import pytesseract

        pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD
    except ImportError:
        pass


def ocr_pdf_page(path: Path, page_index: int) -> str:
    """
    OCR one PDF page using PyMuPDF + Tesseract.

    page_index is zero-based.
    """
    import fitz
    import pytesseract
    from PIL import Image

    setup_tesseract()

    zoom = OCR_DPI / 72
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(str(path)) as doc:
        page = doc[page_index]
        pix = page.get_pixmap(matrix=matrix, alpha=False)

    image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(image, lang=OCR_LANG)

    return cleanup(text)


def read_pdf(path: Path) -> list[dict]:
    reader = PdfReader(str(path))
    pieces = []

    for page_index, page in enumerate(reader.pages):
        page_number = page_index + 1

        text = page.extract_text() or ""
        text = cleanup(text)

        extraction_method = "pdf_text"

        if OCR_ENABLED and len(text) < OCR_MIN_TEXT_CHARS:
            try:
                ocr_text = ocr_pdf_page(path, page_index)

                if len(ocr_text) > len(text):
                    text = ocr_text
                    extraction_method = "ocr"

            except Exception as exc:
                print(f"OCR failed for {path.name} page {page_number}: {exc}")

        if text:
            pieces.append(
                {
                    "text": text,
                    "page": page_number,
                    "extraction_method": extraction_method,
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

    return [
        {
            "text": "\n".join(lines),
            "page": None,
            "extraction_method": "docx",
        }
    ]


def read_text(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="ignore")

    return [
        {
            "text": cleanup(text),
            "page": None,
            "extraction_method": "text",
        }
    ]


def load_file(path: Path) -> list[dict]:
    ext = path.suffix.lower()

    if ext == ".pdf":
        return read_pdf(path)

    if ext == ".docx":
        return read_docx(path)

    if ext in {".txt", ".md"}:
        return read_text(path)

    return []