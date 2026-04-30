import os
os.environ["CHROMA_TELEMETRY_ENABLED"] = "false"

import chromadb
import hashlib
import json
from datetime import datetime
from typing import List, Dict
from app.config import CHROMA_DIR

class VectorStore:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=CHROMA_DIR)
        self.collection = self.client.get_or_create_collection(name="rag_chunks")

    def add_chunks(self, chunks: List[Dict], source_file: str, source_hash: str, embedding_provider):
        """Embeds and stores chunks. Each chunk gets metadata."""
        if not chunks:
            return 0
        texts = [c["text"] for c in chunks]
        embeddings = embedding_provider.embed(texts)
        ids = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{source_hash}_{i}"
            ids.append(chunk_id)
            metadatas.append({
                "file": source_file,
                "page": chunk["page"],
                "chunk": i,
                "source_hash": source_hash,
                "chunking_strategy": "semantic",
                "text_length": len(chunk["text"]),
                "timestamp": datetime.utcnow().isoformat()
            })
        self.collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas
        )
        return len(chunks)

    def delete_by_source_hash(self, source_hash: str):
        self.collection.delete(where={"source_hash": source_hash})

    def query(self, query_embedding: List[float], top_k: int = 5):
        results = self.collection.query(query_embeddings=[query_embedding], n_results=top_k, include=["documents", "metadatas", "distances"])
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]
        return [
            {"text": doc, "metadata": meta, "score": 1 - dist}
            for doc, meta, dist in zip(docs, metas, distances)
        ]

    def get_all_documents(self):
        """Return list of distinct files and their chunk counts."""
        all_metas = self.collection.get(include=["metadatas"])["metadatas"]
        files = {}
        for m in all_metas:
            fname = m["file"]
            if fname not in files:
                files[fname] = {"chunks": 0, "source_hash": m["source_hash"]}
            files[fname]["chunks"] += 1
        return files