
"""Demonstrate session-scoped semantic search from the command line."""

from backend.database import search_similar_chunks
from backend.services.embedding import generate_embedding


def main() -> None:
    """Search document chunks belonging to a specific session."""

    # Set the session ID containing the documents to search.
    session_id = 999

    # Ask a sample question about the uploaded legal document.
    question = "What is the principle of fair trial?"

    # Convert the question into an embedding for semantic retrieval.
    query_embedding = generate_embedding(question)

    # Retrieve the five most relevant chunks from this session only.
    results = search_similar_chunks(
        query_embedding,
        session_id=session_id,
        limit=5,
    )

    print("\n" + "=" * 65)
    print("         DOCUMENT - SEMANTIC SEARCH")
    print("=" * 65)
    print(f"\nSession ID: {session_id}")
    print(f"Question: {question}")
    print(f"Matching passages found: {len(results)}")

    # Display each result with its source metadata and a text preview.
    for rank, result in enumerate(results, start=1):
        print("\n" + "-" * 65)
        print(f"Result {rank}")
        print(f"Document ID : {result['document_id']}")
        print(f"Chunk index : {result['chunk_index']}")
        print(f"Distance    : {result['distance']:.4f}")
        print("\nRelevant passage:")
        print(result["chunk_text"][:700])

    print("\n" + "=" * 65)
    print(
        "Search complete. These are retrieved passages, "
        "not AI-generated answers."
    )
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
