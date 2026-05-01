import hashlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from api.schemas import IngestResponse, ReindexResponse
from config import Settings
from core.document_loader import DocumentLoader
from core.embeddings import EmbeddingFactory
from core.semantic_chunker import SemanticChunkService
from core.state import IndexState
from core.vectorstore import VectorStore


ProgressCallback = Callable[[str], None]


class IngestionPipeline:
    """
    End-to-end document ingestion:

    1. Load text from supported files.
    2. Split pages into semantic chunks.
    3. Generate embeddings.
    4. Store chunks, embeddings, and metadata in Chroma.
    5. Persist index state to skip unchanged files later.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.loader = DocumentLoader()
        self.state = IndexState(settings)
        self.embeddings = EmbeddingFactory.create(settings)
        self.chunker = SemanticChunkService(self.embeddings, settings)
        self.vectorstore = VectorStore(settings)

    def ingest_directory(
        self,
        force_rebuild: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> ReindexResponse:
        files = self.find_supported_files(self.settings.docs_dir)

        details: list[IngestResponse] = []
        indexed = 0
        skipped = 0
        total_chunks = 0

        for file_index, path in enumerate(files, start=1):
            self._report(
                progress_callback,
                f"Processing file {file_index}/{len(files)}: {path.name}",
            )

            result = self.ingest_file(
                path,
                force_rebuild=force_rebuild,
                progress_callback=progress_callback,
            )

            details.append(result)

            if result.status == "indexed":
                indexed += 1
                total_chunks += result.chunks_added
            elif result.status == "skipped":
                skipped += 1

        return ReindexResponse(
            status="complete",
            files_seen=len(files),
            files_indexed=indexed,
            files_skipped=skipped,
            chunks_added=total_chunks,
            details=details,
        )

    def ingest_file(
        self,
        path: Path,
        force_rebuild: bool = False,
        progress_callback: ProgressCallback | None = None,
    ) -> IngestResponse:
        path = Path(path)

        if not path.exists():
            raise FileNotFoundError(f"File not found: {path}")

        self._report(progress_callback, f"Starting ingest: {path.name}")

        source_id = self.state.source_id_for(path)
        source_path = str(path.resolve())

        if not force_rebuild and self.state.is_current(path, source_id):
            self._report(progress_callback, f"Skipping unchanged file: {path.name}")

            return IngestResponse(
                status="skipped",
                file_name=path.name,
                source_id=source_id,
                chunks_added=0,
                reason="File already indexed and unchanged.",
            )

        self._report(progress_callback, f"Deleting old chunks for: {path.name}")
        self.vectorstore.delete_by_source_path(source_path)

        self._report(progress_callback, f"Extracting text from: {path.name}")
        pages = self.loader.load(path)
        self._report(progress_callback, f"Extracted {len(pages)} page(s) from: {path.name}")

        rows: list[dict[str, Any]] = []
        indexed_at = datetime.now(timezone.utc).isoformat()

        for page_index, page in enumerate(pages, start=1):
            self._report(
                progress_callback,
                (
                    f"Semantic chunking {path.name}, "
                    f"page {page.page_number} ({page_index}/{len(pages)})"
                ),
            )

            chunks = self.chunker.split(page.text)

            self._report(
                progress_callback,
                (
                    f"Created {len(chunks)} chunk(s) from "
                    f"{path.name}, page {page.page_number}"
                ),
            )

            for chunk_number, chunk_text in enumerate(chunks, start=1):
                chunk_id = self._chunk_id(
                    source_id=source_id,
                    page_number=page.page_number,
                    chunk_number=chunk_number,
                )

                rows.append(
                    {
                        "chunk_id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "file_name": path.name,
                            "source_path": source_path,
                            "source_id": source_id,
                            "page_number": page.page_number,
                            "chunk_number": chunk_number,
                            "index_version": self.settings.index_version,
                            "indexed_at": indexed_at,
                        },
                    }
                )

        if not rows:
            self._report(progress_callback, f"No readable text found in: {path.name}")

            return IngestResponse(
                status="skipped",
                file_name=path.name,
                source_id=source_id,
                chunks_added=0,
                reason="No readable text found.",
            )

        batches = list(self._batched(rows, self.settings.embed_batch_size))

        self._report(
            progress_callback,
            f"Embedding {len(rows)} chunk(s) in {len(batches)} batch(es) for: {path.name}",
        )

        for batch_index, batch in enumerate(batches, start=1):
            self._report(
                progress_callback,
                f"Embedding batch {batch_index}/{len(batches)} for: {path.name}",
            )

            texts = [row["text"] for row in batch]
            embeddings = self.embeddings.embed_documents(texts)

            self._report(
                progress_callback,
                f"Writing batch {batch_index}/{len(batches)} to Chroma for: {path.name}",
            )

            self.vectorstore.upsert_chunks(
                ids=[row["chunk_id"] for row in batch],
                texts=texts,
                embeddings=embeddings,
                metadatas=[row["metadata"] for row in batch],
            )

        self.state.update(
            path=path,
            source_id=source_id,
            chunks_added=len(rows),
        )

        self._report(progress_callback, f"Finished indexing {path.name}: {len(rows)} chunk(s)")

        return IngestResponse(
            status="indexed",
            file_name=path.name,
            source_id=source_id,
            chunks_added=len(rows),
        )

    def find_supported_files(self, folder: Path) -> list[Path]:
        files: list[Path] = []

        if not folder.exists():
            return files

        for path in folder.rglob("*"):
            if path.is_file() and path.suffix.lower() in DocumentLoader.SUPPORTED_EXTENSIONS:
                files.append(path)

        return sorted(files)

    def _chunk_id(
        self,
        source_id: str,
        page_number: int,
        chunk_number: int,
    ) -> str:
        raw = f"{source_id}:p{page_number}:c{chunk_number}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _batched(self, items: list[Any], batch_size: int):
        for index in range(0, len(items), batch_size):
            yield items[index : index + batch_size]

    def _report(
        self,
        progress_callback: ProgressCallback | None,
        message: str,
    ) -> None:
        print(message, flush=True)

        if progress_callback:
            progress_callback(message)