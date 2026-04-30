from app.rag.retrieve import Retriever
from app.rag.prompts import build_prompt, load_settings
from app.providers.base import LLMProvider
from app.providers.ollama_provider import OllamaProvider
from app.providers.openai_provider import OpenAIProvider
from app.providers.gemini_provider import GeminiProvider
from app.providers.deepseek_provider import DeepSeekProvider

class RAGPipeline:
    def __init__(self):
        self.retriever = Retriever()

    def _get_provider(self, provider_name: str):
        if provider_name == "ollama":
            return OllamaProvider()
        elif provider_name == "openai":
            return OpenAIProvider()
        elif provider_name == "gemini":
            return GeminiProvider()
        elif provider_name == "deepseek":
            return DeepSeekProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    def answer(self, question: str, provider_name: str, model_name: str,
               top_k: int = None, temperature: float = None, mode: str = None):
        settings = load_settings()
        if top_k is None:
            top_k = settings["top_k"]
        if temperature is None:
            temperature = settings["temperature"]
        if mode is None:
            mode = settings["mode"]

        # Retrieve
        results = self.retriever.search(question, top_k=top_k)
        if not results:
            return {"answer": "No relevant documents found.", "sources": []}

        # Build prompt
        system_prompt, user_prompt = build_prompt(question, results, mode=mode, settings=settings)

        # Get provider
        provider = self._get_provider(provider_name)
        answer_text = provider.generate(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model=model_name,
            temperature=temperature
        )

        # Format sources for display
        sources = []
        seen = set()
        for r in results:
            m = r["metadata"]
            key = f"{m['file']}_p{m['page']}_c{m['chunk']}"
            if key not in seen:
                sources.append({
                    "file": m["file"],
                    "page": m["page"],
                    "chunk": m["chunk"],
                    "text_snippet": r["text"][:200]
                })
                seen.add(key)

        return {
            "answer": answer_text,
            "sources": sources
        }