from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from config import Settings


class EmbeddingFactory:
    """
    Builds the locked OpenAI embedding model for retrieval/indexing.
    """

    @staticmethod
    def create(settings: Settings) -> Embeddings:
        if not settings.openai_api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAI embeddings.")

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.openai_api_key,
        )