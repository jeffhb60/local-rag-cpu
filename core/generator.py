from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from config import Settings
from core.embeddings import EmbeddingFactory
from core.llm_factory import LLMFactory
from core.vectorstore import VectorStore
from core.reranker import CrossEncoderReranker


class RAGGenerator:
    """
    Handles retrieval, prompt construction, and answer generation.

    Provider/model choices are intentionally locked:
    - Chat provider: deepseek
    - Chat model: DeepSeek-V4-Pro
    - Embeddings: text-embedding-3-small
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        self.embeddings = EmbeddingFactory.create(settings)
        self.vectorstore = VectorStore(settings)

        self.reranker = None
        if settings.reranker_enabled:
            self.reranker = CrossEncoderReranker(settings.reranker_model)

    def answer(
            self,
            question: str,
            top_k: int | None = None,
            temperature: float | None = None,
            strictness: bool | None = None,
            system_prompt: str | None = None,
            rag_instruction_template: str | None = None,
            context_format: str | None = None,
    ) -> dict[str, Any]:
        # Final number of chunks you want to send to the LLM.
        # If reranking is enabled, this is mostly a fallback.
        top_k_final = top_k or self.settings.top_k_default
        top_k_final = max(1, min(top_k_final, 50))

        # If reranking is enabled:
        #   retrieve more candidates first, for example 20.
        # If reranking is disabled:
        #   retrieve only top_k_final.
        candidate_k = (
            self.settings.retrieval_candidate_k
            if self.settings.reranker_enabled
            else top_k_final
        )

        # Make sure candidate_k is at least top_k_final and no more than 50.
        candidate_k = max(top_k_final, min(candidate_k, 50))

        # Embed the user's question.
        query_embedding = self.embeddings.embed_query(question)

        # Retrieve candidate chunks from Chroma.
        chunks = self.vectorstore.query(
            question=question,
            query_embedding=query_embedding,
            top_k=candidate_k,
        )

        # Filter out weak retrieval matches.
        # Lower cosine distance generally means more similar.
        chunks = [
            chunk
            for chunk in chunks
            if chunk.get("distance", 1.0) <= self.settings.max_retrieval_distance
        ]

        if not chunks:
            return {
                "answer": "I could not find that in the indexed documents.",
                "retrieved_chunks": [],
            }

        # Rerank candidate chunks, then keep only the strongest chunks.
        # This is the key new section.
        if self.reranker is not None:
            chunks = self.reranker.rerank(
                question=question,
                chunks=chunks,
                top_k=self.settings.rerank_top_k,
            )
        else:
            chunks = chunks[:top_k_final]

        if not chunks:
            return {
                "answer": "I could not find that in the indexed documents.",
                "retrieved_chunks": [],
            }

        # Build the context that gets sent to the LLM.
        context = self._format_context(
            chunks=chunks,
            context_format=context_format or self.settings.context_format,
        )

        strictness_final = (
            strictness
            if strictness is not None
            else self.settings.strictness_mode
        )

        prompt_template = (
                rag_instruction_template
                or self.settings.rag_instruction_template
        )

        if "{context}" not in prompt_template or "{question}" not in prompt_template:
            raise ValueError(
                "RAG instruction template must include {context} and {question}."
            )

        if strictness_final:
            prompt_template = self._add_strictness_guard(prompt_template)

        final_prompt = prompt_template.format(
            context=context,
            question=question,
        )

        llm = LLMFactory.create(
            settings=self.settings,
            temperature=temperature,
        )

        response = llm.invoke(
            [
                SystemMessage(
                    content=system_prompt or self.settings.system_prompt
                ),
                HumanMessage(content=final_prompt),
            ]
        )

        return {
            "answer": response.content,
            "retrieved_chunks": chunks,
        }

    def _format_context(
        self,
        chunks: list[dict[str, Any]],
        context_format: str,
    ) -> str:
        blocks: list[str] = []

        for index, chunk in enumerate(chunks, start=1):
            metadata = chunk["metadata"]

            blocks.append(
                context_format.format(
                    source_number=index,
                    file_name=metadata.get("file_name", "unknown"),
                    page_number=metadata.get("page_number", ""),
                    chunk_number=metadata.get("chunk_number", ""),
                    text=chunk["text"],
                )
            )

        return "\n\n---\n\n".join(blocks)

    def _add_strictness_guard(self, template: str) -> str:
        return (
            template
            + "\n\nFinal grounding check:\n"
            "Before answering, verify that every factual claim is supported by the context. "
            "If not, say: \"I could not find that in the indexed documents.\""
        )