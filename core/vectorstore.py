from typing import Any

import chromadb

from config import Settings


class VectorStore:
    """
    Thin wrapper around ChromaDB.

    Embeddings are generated outside this class and passed in explicitly.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = chromadb.PersistentClient(path=str(settings.chroma_dir))
        self.collection = self.client.get_or_create_collection(
            name=settings.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert_chunks(
        self,
        ids: list[str],
        texts: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]],
    ) -> None:
        if not ids:
            return

        self.collection.upsert(
            ids=ids,
            documents=texts,
            embeddings=embeddings,
            metadatas=metadatas,
        )

    def query(
        self,
        question: str,
        query_embedding: list[float],
        top_k: int,
    ) -> list[dict[str, Any]]:
        raw = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        documents = raw.get("documents", [[]])[0]
        metadatas = raw.get("metadatas", [[]])[0]
        distances = raw.get("distances", [[]])[0]
        ids = raw.get("ids", [[]])[0]

        chunks: list[dict[str, Any]] = []

        for chunk_id, text, metadata, distance in zip(
            ids,
            documents,
            metadatas,
            distances,
        ):
            chunks.append(
                {
                    "chunk_id": chunk_id,
                    "text": text,
                    "metadata": metadata,
                    "distance": distance,
                }
            )

        return chunks

    def delete_by_source_path(self, source_path: str) -> None:
        try:
            self.collection.delete(where={"source_path": source_path})
        except Exception as exc:
            print(f"[vectorstore] delete_by_source_path ignored: {exc}", flush=True)

    def count(self) -> int:
        return self.collection.count()