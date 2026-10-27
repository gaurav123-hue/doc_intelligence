
"""Split extracted document text into overlapping chunks."""


def chunk_text(
    text: str,
    chunk_size: int = 1000,
    overlap: int = 150,
) -> list[str]:
    """Split text into chunks while preserving some neighboring context."""

    # Reject invalid settings to avoid infinite loops or empty chunks.
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than zero")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    # Ignore leading and trailing whitespace before chunking.
    text = text.strip()

    # Empty documents should produce no chunks.
    if not text:
        return []

    chunks = []
    start = 0

    # Move through the text using a step smaller than the chunk size.
    step = chunk_size - overlap

    while start < len(text):
        # Keep each chunk within the configured character limit.
        end = start + chunk_size
        chunk = text[start:end].strip()

        # Do not add empty chunks if a slice contains only whitespace.
        if chunk:
            chunks.append(chunk)

        # Advance while retaining the requested overlap.
        start += step

    return chunks
