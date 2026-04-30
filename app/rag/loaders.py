import os
from pypdf import PdfReader
from docx import Document
import markdown

def load_txt(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    return [{"text": text, "page": 1}]

def load_md(file_path: str):
    with open(file_path, "r", encoding="utf-8") as f:
        md_text = f.read()
    html = markdown.markdown(md_text)
    # simple plain text extraction (remove tags)
    import re
    text = re.sub(r'<[^>]+>', '', html)
    return [{"text": text, "page": 1}]

def load_pdf(file_path: str):
    reader = PdfReader(file_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text()
        if text:
            pages.append({"text": text.strip(), "page": i})
    return pages

def load_docx(file_path: str):
    doc = Document(file_path)
    pages = []
    current_page = 1
    current_text = []
    for para in doc.paragraphs:
        # Check for explicit page break
        if para.paragraph_format.page_break_before and current_text:
            pages.append({"text": "\n".join(current_text), "page": current_page})
            current_page += 1
            current_text = []
        current_text.append(para.text)
    if current_text:
        pages.append({"text": "\n".join(current_text), "page": current_page})
    return pages if pages else [{"text": "", "page": 1}]

LOADERS = {
    ".txt": load_txt,
    ".md": load_md,
    ".pdf": load_pdf,
    ".docx": load_docx
}

def load_document(file_path: str):
    ext = os.path.splitext(file_path)[1].lower()
    loader = LOADERS.get(ext)
    if not loader:
        raise ValueError(f"Unsupported file type: {ext}")
    return loader(file_path)