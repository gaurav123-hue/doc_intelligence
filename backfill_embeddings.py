
"""Generate and save embeddings for chunks that do not have them yet."""

from backend.database import (
    get_chunks_without_embeddings,
    save_chunk_embedding,
)
from backend.services.embedding import generate_embedding


def main() -> None:
    """Embed all pending chunks and report progress."""

    # Fetch only chunks whose embedding column is currently NULL.
    chunks = get_chunks_without_embeddings()

    if not chunks:
        print("All document chunks already have embeddings.")
        return

    print(f"Found {len(chunks)} chunks awaiting embeddings.")

    # Process one chunk at a time to keep memory use manageable.
    for index, chunk in enumerate(chunks, start=1):
        # Convert the stored text into a normalized 384-dimensional vector.
        embedding = generate_embedding(chunk["chunk_text"])

        # Save the vector to the same database row as its source text.
        save_chunk_embedding(chunk["id"], embedding)

        print(f"Embedded chunk {index}/{len(chunks)} (ID: {chunk['id']})")

    print("Embedding backfill completed successfully.")


if __name__ == "__main__":
    main()
