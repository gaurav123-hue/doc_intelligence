
"""Demonstrate semantic search from the command line."""

from backend.database import search_similar_chunks
from backend.services.embedding import generate_embedding


def main() -> None:
    """Search stored document chunks and display the best matches."""

    # Ask a sample question about the uploaded legal document.
    question = "What is the principle of fair trial?"

    # Convert the question into an embedding for semantic retrieval.
    query_embedding = generate_embedding(question)

    # Retrieve the five most relevant chunks from PostgreSQL.
    results = search_similar_chunks(query_embedding, limit=5)

    print("\n" + "=" * 65)
    print("         DOCUMENT  - SEMANTIC SEARCH")
    print("=" * 65)
    print(f"\nQuestion: {question}")
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
    print("Search complete. These are retrieved passages, not AI-generated answers.")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    main()
