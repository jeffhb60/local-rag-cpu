import json
import requests

from config import OLLAMA_URL, CHAT_MODEL, EMBED_MODEL, GENERATE_TIMEOUT, EMBED_TIMEOUT


class OllamaError(RuntimeError):
    pass


def embed_one(text: str) -> list[float]:
    return embed_many([text])[0]


def embed_many(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    url = f"{OLLAMA_URL}/api/embed"
    payload = {
        "model": EMBED_MODEL,
        "input": texts,
    }

    try:
        response = requests.post(url, json=payload, timeout=EMBED_TIMEOUT)
        response.raise_for_status()
        return response.json()["embeddings"]
    except requests.exceptions.ConnectionError as exc:
        raise OllamaError("Could not reach Ollama. Start it, then try again.") from exc
    except requests.exceptions.HTTPError as exc:
        raise OllamaError(f"Ollama returned an error: {exc.response.text}") from exc


def generate_stream(prompt: str):
    """Yields chunks of the generated response in real-time."""
    url = f"{OLLAMA_URL}/api/generate"
    payload = {
        "model": CHAT_MODEL,
        "prompt": prompt,
        "stream": True,
        "options": {
            "temperature": 0.1,
            "num_ctx": 4096,
        },
    }

    try:
        # Stream is set to True here
        response = requests.post(url, json=payload, timeout=GENERATE_TIMEOUT, stream=True)
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                data = json.loads(line)
                yield data.get("response", "")

    except requests.exceptions.ConnectionError as exc:
        raise OllamaError("Could not reach Ollama. Start it, then try again.") from exc
    except requests.exceptions.HTTPError as exc:
        raise OllamaError(f"Ollama returned an error: {exc.response.text}") from exc