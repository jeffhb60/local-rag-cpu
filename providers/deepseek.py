import os
import requests


class DeepSeekProvider:
    def generate(self, prompt: str, model: str | None = None) -> str:
        api_key = os.getenv("DEEPSEEK_API_KEY")
        model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

        if not api_key:
            raise RuntimeError("DEEPSEEK_API_KEY is missing.")

        response = requests.post(
            "https://api.deepseek.com/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.1,
                "max_tokens": 300,
            },
            timeout=120,
        )

        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"].strip()