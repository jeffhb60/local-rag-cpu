from langchain_core.embeddings import Embeddings
from langchain_experimental.text_splitter import SemanticChunker
from langchain_text_splitters import RecursiveCharacterTextSplitter

from config import Settings


class SemanticChunkService:
    """
    Splits extracted document text into meaning-aware chunks.

    SemanticChunker groups text by semantic similarity rather than
    blindly splitting every N characters. A recursive splitter is used
    as a safety fallback for overly long chunks.
    """

    def __init__(self, embeddings: Embeddings, settings: Settings):
        self.settings = settings

        self.semantic_chunker = SemanticChunker(
            embeddings,
            breakpoint_threshold_type=settings.semantic_breakpoint_type,
            breakpoint_threshold_amount=settings.semantic_breakpoint_amount,
        )

        self.length_splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.max_chunk_chars,
            chunk_overlap=settings.chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split(self, text: str) -> list[str]:
        clean_text = self._clean_text(text)

        if not clean_text:
            return []

        try:
            semantic_chunks = self.semantic_chunker.split_text(clean_text)
        except Exception as exc:
            print(f"[chunker] semantic chunking failed; using fallback: {exc}", flush=True)
            semantic_chunks = [clean_text]

        semantic_chunks = self._merge_small_chunks(semantic_chunks)

        final_chunks: list[str] = []

        for chunk in semantic_chunks:
            if len(chunk) <= self.settings.max_chunk_chars:
                final_chunks.append(chunk)
            else:
                final_chunks.extend(self.length_splitter.split_text(chunk))

        return [chunk.strip() for chunk in final_chunks if chunk.strip()]

    def _clean_text(self, text: str) -> str:
        lines = [line.strip() for line in text.splitlines()]
        return "\n".join(line for line in lines if line)

    def _merge_small_chunks(self, chunks: list[str]) -> list[str]:
        merged: list[str] = []
        buffer = ""

        for chunk in chunks:
            chunk = chunk.strip()

            if not chunk:
                continue

            if len(buffer) < self.settings.min_chunk_chars:
                buffer = f"{buffer}\n\n{chunk}".strip()
            else:
                merged.append(buffer)
                buffer = chunk

        if buffer:
            merged.append(buffer)

        return merged