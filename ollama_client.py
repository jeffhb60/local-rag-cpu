import requests

from config import OLLAMA_URL, EMBED_MODEL


class OllamaError(RuntimeError):
    pass


def _post(endpoint: str, payload: dict, timeout: int = 120) -> dict:
    url = f"{OLLAMA_URL}{endpoint}"

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        response.raise_for_status()
        return response.json()

    except requests.exceptions.ConnectionError as exc:
        raise OllamaError(
            "Could not reach Ollama. Start it, then try again."
        ) from exc

    except requests.exceptions.HTTPError as exc:
        raise OllamaError(f"Ollama returned an error: {response.text}") from exc


def embed_one(text: str) -> list[float]:
    return embed_many([text])[0]


def embed_many(texts: list[str]) -> list[list[float]]:
    if not texts:
        return []

    data = _post(
        "/api/embed",
        {
            "model": EMBED_MODEL,
            "input": texts,
        },
        timeout=180,
    )

    return data["embeddings"]