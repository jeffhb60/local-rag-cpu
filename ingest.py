import hashlib
from pathlib import Path

from tqdm import tqdm

from config import DOCS_DIR, EMBED_BATCH_SIZE, INDEX_VERSION
from loaders import SUPPORTED_FILES, load_file
from ollama_client import embed_many
from splitter import split_text
from store import get_collection


def file_stamp(path: Path) -> str:
    stat = path.stat()
    raw = f"{path.resolve()}::{stat.st_size}::{stat.st_mtime_ns}::{INDEX_VERSION}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:16]


def row_id(source_key: str, page, chunk_number: int) -> str:
    raw = f"{source_key}::{page}::{chunk_number}"
    return hashlib.sha1(raw.encode("utf-8")).hexdigest()


def find_docs() -> list[Path]:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)

    return sorted(
        path
        for path in DOCS_DIR.rglob("*")
        if path.is_file() and path.suffix.lower() in SUPPORTED_FILES
    )


def batched(items: list, size: int):
    for start in range(0, len(items), size):
        yield items[start : start + size]


def build_rows(path: Path) -> list[dict]:
    source_path = str(path.resolve())
    source_id = file_stamp(path)
    rows = []
    chunk_number = 0

    for part in load_file(path):
        page = part.get("page")
        used_ocr = bool(part.get("ocr", False))

        for chunk in split_text(part["text"]):
            rows.append(
                {
                    "id": row_id(source_id, page, chunk_number),
                    "text": chunk,
                    "meta": {
                        "file": path.name,
                        "source_path": source_path,
                        "source_id": source_id,
                        "page": page if page is not None else "",
                        "chunk": chunk_number,
                        "ocr": used_ocr,
                    },
                }
            )
            chunk_number += 1

    return rows


def already_indexed(collection, source_id: str) -> bool:
    try:
        existing = collection.get(where={"source_id": source_id}, limit=1)
        return bool(existing and existing.get("ids"))
    except Exception:
        return False


def index_file(collection, path: Path) -> None:
    source_id = file_stamp(path)

    if already_indexed(collection, source_id):
        print(f"skipped: {path.name} is already indexed")
        return

    source_path = str(path.resolve())

    try:
        collection.delete(where={"source_path": source_path})
    except Exception:
        pass

    rows = build_rows(path)

    if not rows:
        print(f"skip: {path.name} has no readable text")
        return

    for group in tqdm(list(batched(rows, EMBED_BATCH_SIZE)), desc=path.name):
        texts = [row["text"] for row in group]
        embeddings = embed_many(texts)

        collection.upsert(
            ids=[row["id"] for row in group],
            documents=texts,
            embeddings=embeddings,
            metadatas=[row["meta"] for row in group],
        )

    ocr_chunks = sum(1 for row in rows if row["meta"].get("ocr"))
    print(f"indexed: {path.name} ({len(rows)} chunks, {ocr_chunks} OCR chunks)")


def main() -> None:
    docs = find_docs()

    if not docs:
        print(f"No files found in {DOCS_DIR}")
        return

    collection = get_collection()

    for path in docs:
        try:
            index_file(collection, path)
        except Exception as exc:
            print(f"failed: {path.name} -- {exc}")

    print("done")


if __name__ == "__main__":
    main()