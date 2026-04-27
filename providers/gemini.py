import os
from google import genai


class GeminiProvider:
    def generate(self, prompt: str, model: str | None = None) -> str:
        api_key = os.getenv("GEMINI_API_KEY")
        model = model or os.getenv("GEMINI_MODEL", "gemini-1.5-flash")

        if not api_key:
            raise RuntimeError("GEMINI_API_KEY is missing.")

        client = genai.Client(api_key=api_key)

        response = client.models.generate_content(
            model=model,
            contents=prompt,
        )

        return response.text.strip()