from openai import OpenAI
from app.config import OLLAMA_BASE_URL
from .base import LLMProvider

class OllamaProvider(LLMProvider):
    def generate(self, system_prompt, user_prompt, model, temperature):
        client = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")  # api_key required but unused
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content