from sentence_transformers import SentenceTransformer
from app.config import EMBEDDING_MODEL

class EmbeddingProvider:
    def __init__(self, model_name: str = None):
        self.model_name = model_name or EMBEDDING_MODEL
        self.model = SentenceTransformer(self.model_name)

    def embed(self, texts):
        return self.model.encode(texts).tolist()

    def embed_query(self, text):
        return self.model.encode(text).tolist()