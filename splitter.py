from config import CHUNK_CHARS, CHUNK_OVERLAP

def split_text(text: str) -> list[str]:
    text = text.strip()

    if not text:
        return []

    chunks = []
    start = 0
    text_length = len(text)

    while start < text_length:
        stop = start + CHUNK_CHARS

        # Prevent slicing words in half by finding the nearest preceding space
        if stop < text_length:
            boundary = text.rfind(' ', start + CHUNK_CHARS - CHUNK_OVERLAP, stop)
            if boundary != -1:
                stop = boundary

        chunk = text[start:stop].strip()

        if chunk:
            chunks.append(chunk)

        start = stop - CHUNK_OVERLAP

    return chunks