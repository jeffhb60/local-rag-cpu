from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Central app configuration.

    Chat is locked to DeepSeek.
    Embeddings are locked to OpenAI text-embedding-3-small.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # App
    app_name: str = "FastAPI RAG Study Assistant"
    app_env: str = "development"

    # Paths
    docs_dir: Path = Path("data/docs")
    chroma_dir: Path = Path("chroma_db")
    index_state_path: Path = Path("data/index_state.json")

    # Chroma
    collection_name: str = "rag_documents"
    index_version: str = "semantic-v2-openai-embeddings"

    # Locked embeddings
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"

    # Locked chat generation
    chat_provider: str = "deepseek"
    chat_model: str = "deepseek-v4-pro"

    # API keys
    openai_api_key: str | None = None
    deepseek_api_key: str | None = None

    # DeepSeek
    deepseek_base_url: str = "https://api.deepseek.com"

    # RAG settings
    top_k_default: int = 8
    temperature_default: float = 0.3
    strictness_mode: bool = True

    # Semantic chunking
    semantic_breakpoint_type: str = "percentile"
    semantic_breakpoint_amount: int = 85
    min_chunk_chars: int = 250
    max_chunk_chars: int = 1800
    chunk_overlap: int = 150
    embed_batch_size: int = 32

    # Prompting
    system_prompt: str = (
        "You are a careful retrieval-augmented assistant. "
        "Answer only from the provided context. "
        "Do not invent facts."
    )

    rag_instruction_template: str = (
        "Use the context below to answer the question.\n\n"
        "Rules:\n"
        "1. Answer only using the provided context.\n"
        "2. Cite sources using the bracketed source number, file name, page, and chunk when available.\n"
        "3. Use the controlling legal terms from the context when they are relevant.\n"
        "4. Do not over-paraphrase important doctrines, tests, rights, clauses, or standards.\n"
        "5. If the answer is not supported by the context, say: "
        "\"I could not find that in the indexed documents.\"\n"
        "6. Be concise but complete.\n\n"
        "Context:\n{context}\n\n"
        "Question:\n{question}\n\n"
        "Answer:"
    )

    context_format: str = (
        "[{source_number}] File: {file_name} | Page: {page_number} | Chunk: {chunk_number}\n"
        "{text}"
    )

    def ensure_directories(self) -> None:
        self.docs_dir.mkdir(parents=True, exist_ok=True)
        self.chroma_dir.mkdir(parents=True, exist_ok=True)
        self.index_state_path.parent.mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_directories()