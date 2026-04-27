import os
from openai import OpenAI


class OpenAIProvider:
    def generate(self, prompt: str, model: str | None = None) -> str:
        api_key = os.getenv("OPENAI_API_KEY")
        model = model or os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is missing.")

        client = OpenAI(api_key=api_key)

        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=300,
        )

        return response.choices[0].message.content.strip()