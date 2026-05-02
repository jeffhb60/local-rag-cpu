from __future__ import annotations

from typing import Any


class CrossEncoderReranker:
    """
    Local cross-encoder reranker.

    It scores each question/chunk pair directly.
    This is slower than vector search but usually more accurate for final ranking.
    """

    def __init__(self, model_name: str):
        try:
            from sentence_transformers import CrossEncoder
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required for reranking. "
                "Install it with: pip install sentence-transformers"
            ) from exc

        self.model = CrossEncoder(model_name)

    def rerank(
        self,
        question: str,
        chunks: list[dict[str, Any]],
        top_k: int,
    ) -> list[dict[str, Any]]:
        if not chunks:
            return []

        pairs = [
            [question, chunk["text"]]
            for chunk in chunks
        ]

        scores = self.model.predict(pairs)

        scored_chunks: list[dict[str, Any]] = []

        for chunk, score in zip(chunks, scores):
            updated_chunk = dict(chunk)
            updated_metadata = dict(updated_chunk.get("metadata", {}))

            updated_chunk["rerank_score"] = float(score)
            updated_metadata["rerank_score"] = float(score)
            updated_chunk["metadata"] = updated_metadata

            scored_chunks.append(updated_chunk)

        scored_chunks.sort(
            key=lambda chunk: chunk.get("rerank_score", float("-inf")),
            reverse=True,
        )

        return scored_chunks[:top_k]