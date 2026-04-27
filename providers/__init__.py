from providers.ollama import OllamaProvider
from providers.deepseek import DeepSeekProvider
from providers.gemini import GeminiProvider
from providers.openai_chatgpt import OpenAIProvider

PROVIDERS = {
    "local": OllamaProvider(),
    "ollama": OllamaProvider(),
    "deepseek": DeepSeekProvider(),
    "gemini": GeminiProvider(),
    "openai": OpenAIProvider(),
}


def generate_answer(
    prompt: str,
    provider_name: str = "local",
    model: str | None = None,
) -> str:
    provider_name = provider_name.lower().strip()

    if provider_name not in PROVIDERS:
        valid = ", ".join(PROVIDERS)
        raise ValueError(f"Unknown provider '{provider_name}'. Valid options: {valid}")

    return PROVIDERS[provider_name].generate(prompt, model=model)