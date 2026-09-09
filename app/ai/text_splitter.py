import re


def split_text(text: str, chunk_size: int = 1000, chunk_overlap: int = 150) -> list[str]:
    """Split normalized text into overlapping, word-boundary-aware chunks."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")
    if chunk_overlap < 0 or chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be between 0 and chunk_size - 1")

    normalized = re.sub(r"\s+", " ", text).strip()
    if not normalized:
        return []

    chunks: list[str] = []
    start = 0

    while start < len(normalized):
        proposed_end = min(start + chunk_size, len(normalized))
        end = proposed_end

        if proposed_end < len(normalized):
            boundary = normalized.rfind(" ", start + 1, proposed_end + 1)
            if boundary > start:
                end = boundary

        chunk = normalized[start:end].strip()
        if chunk:
            chunks.append(chunk)

        if end >= len(normalized):
            break

        next_start = max(end - chunk_overlap, start + 1)
        if next_start > 0 and normalized[next_start - 1] != " ":
            next_boundary = normalized.find(" ", next_start, end)
            if next_boundary != -1:
                next_start = next_boundary + 1
        start = next_start

    return chunks
