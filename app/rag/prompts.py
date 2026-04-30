import json
from app.config import SETTINGS_FILE

def load_settings():
    with open(SETTINGS_FILE, "r") as f:
        return json.load(f)

def build_prompt(question: str, contexts: list, mode: str = None, settings: dict = None):
    if settings is None:
        settings = load_settings()
    if mode is None:
        mode = settings.get("mode", "strict")
    system = settings["system_prompt"]
    context_template = settings["context_template"]
    top_k = settings.get("top_k", 5)

    # Build context string
    context_parts = []
    for i, ctx in enumerate(contexts[:top_k]):
        meta = ctx["metadata"]
        part = context_template.format(
            index=i+1,
            file=meta["file"],
            page=meta["page"],
            chunk=meta["chunk"],
            text=ctx["text"]
        )
        context_parts.append(part)
    context_str = "\n\n".join(context_parts)

    # Choose RAG instruction based on mode
    if mode == "strict":
        instruction = (
            "Answer ONLY using the provided context. If the answer is not directly supported, "
            "say 'I cannot answer based on the provided documents.' Cite sources like [1], [2]."
        )
    elif mode == "assisted":
        instruction = (
            "Use the context as primary source. You may add general knowledge, but clearly mark "
            "which parts come from context (cite as [1]) and which are your own explanation."
        )
    else:  # open
        instruction = (
            "Use the context when helpful. You can freely discuss the topic. "
            "If using context, cite relevant sources."
        )

    rag_template = settings.get("rag_prompt_template", "{context}\n\n{question}")
    # Build final user message
    user_content = rag_template.format(context=context_str, question=question)
    full_instruction = f"{instruction}\n\n{user_content}"

    return system, full_instruction