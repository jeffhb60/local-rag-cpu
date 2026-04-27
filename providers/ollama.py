import requests

from config import OLLAMA_URL, CHAT_MODEL


class OllamaProvider:
    def generate(self, prompt: str, model: str | None = None) -> str:
        model = model or CHAT_MODEL

        response = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_ctx": 4096,
                },
            },
            timeout=300,
        )

        response.raise_for_status()
        return response.json().get("response", "").strip()