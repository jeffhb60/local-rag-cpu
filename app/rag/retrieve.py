from app.rag.embeddings import EmbeddingProvider
from app.rag.store import VectorStore

class Retriever:
    def __init__(self):
        self.store = VectorStore()
        self.embedder = EmbeddingProvider()

    def search(self, query: str, top_k: int = 5):
        q_emb = self.embedder.embed_query(query)
        return self.store.query(q_emb, top_k)