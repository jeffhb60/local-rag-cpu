from openai import OpenAI
from app.config import OPENAI_API_KEY, OPENAI_BASE_URL
from .base import LLMProvider

class OpenAIProvider(LLMProvider):
    def generate(self, system_prompt, user_prompt, model, temperature):
        client = OpenAI(api_key=OPENAI_API_KEY, base_url=OPENAI_BASE_URL)
        response = client.chat.completions.create(
            model=model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
        )
        return response.choices[0].message.content