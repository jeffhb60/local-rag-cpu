from langchain_core.embeddings import Embeddings
from langchain_openai import OpenAIEmbeddings

from config import Settings


class EmbeddingFactory:
    """
    Builds the locked DeepSeek embedding model.

    This assumes DeepSeek exposes an OpenAI-compatible embeddings endpoint
    at settings.deepseek_base_url.

    Requested locked model:
    - DeepSeek-V4-Embed
    """

    @staticmethod
    def create(settings: Settings) -> Embeddings:
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek embeddings.")

        return OpenAIEmbeddings(
            model=settings.embedding_model,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )