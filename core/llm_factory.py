from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import ChatOpenAI

from config import Settings


class LLMFactory:
    """
    Creates the locked DeepSeek chat model.

    Requested locked model:
    - DeepSeek-V4-Pro
    """

    @staticmethod
    def create(
        settings: Settings,
        temperature: float | None = None,
    ) -> BaseChatModel:
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek chat.")

        temp = (
            temperature
            if temperature is not None
            else settings.temperature_default
        )

        return ChatOpenAI(
            model=settings.chat_model,
            temperature=temp,
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url,
        )