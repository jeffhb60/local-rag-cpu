from config import CHUNK_CHARS, CHUNK_OVERLAP


def split_text(text: str) -> list[str]:
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0

    while start < len(text):
        stop = start + CHUNK_CHARS
        chunk = text[start:stop].strip()

        if chunk:
            chunks.append(chunk)

        start += CHUNK_CHARS - CHUNK_OVERLAP

    return chunks