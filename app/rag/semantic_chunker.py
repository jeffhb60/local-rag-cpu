from typing import List, Dict
import numpy as np
from sentence_transformers import SentenceTransformer

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

class SemanticChunker:
    def __init__(self, model: SentenceTransformer, threshold: float = 0.5,
                 min_chunk_size: int = 50, max_chunk_size: int = 1500):
        self.model = model
        self.threshold = threshold
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk_pages(self, pages: List[Dict[str, object]]):
        """Split each page into paragraphs, then merge based on semantic similarity."""
        all_paragraphs = []
        for page in pages:
            text: str = page["text"]
            page_num = page["page"]
            # split by double newline as paragraph delimiter
            paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
            for para in paragraphs:
                all_paragraphs.append({"text": para, "page": page_num})
        if not all_paragraphs:
            return []

        embeddings = self.model.encode([p["text"] for p in all_paragraphs])
        chunks = []
        current_chunk = {"text": all_paragraphs[0]["text"], "page": all_paragraphs[0]["page"]}
        current_emb = embeddings[0]

        for i in range(1, len(all_paragraphs)):
            sim = cosine_similarity(current_emb, embeddings[i])
            # if similar enough and combined length under max, merge
            if sim >= self.threshold and len(current_chunk["text"]) + len(all_paragraphs[i]["text"]) <= self.max_chunk_size:
                current_chunk["text"] += "\n\n" + all_paragraphs[i]["text"]
                # average embedding for the merged chunk
                current_emb = (current_emb + embeddings[i]) / 2
            else:
                if len(current_chunk["text"]) >= self.min_chunk_size:
                    chunks.append(current_chunk)
                current_chunk = {"text": all_paragraphs[i]["text"], "page": all_paragraphs[i]["page"]}
                current_emb = embeddings[i]
        if current_chunk["text"] and len(current_chunk["text"]) >= self.min_chunk_size:
            chunks.append(current_chunk)
        return chunks