
"""Automated tests for RAG citation validation and answer generation."""

import pytest

from backend.services.rag import answer_question, validate_citations


@pytest.fixture
def retrieved_chunks():
    """Provide sample chunks returned by semantic retrieval."""

    return [
        {"document_id": 7, "chunk_id": 59},
        {"document_id": 7, "chunk_id": 75},
        {"document_id": 7, "chunk_id": 56},
    ]


@pytest.mark.parametrize(
    "answer",
    [
        "Fair trial protects rights. (Document ID: 7, Chunk ID: 59)",
        "Fair trial protects rights. 【Document 7, Chunk 75】",
    ],
)
def test_valid_citation_formats(answer, retrieved_chunks):
    """Verify that supported citation formats are recognized."""

    result = validate_citations(answer, retrieved_chunks)

    assert result["is_valid"] is True
    assert result["invalid_sources"] == []
    assert len(result["cited_sources"]) == 1


def test_invalid_citation(retrieved_chunks):
    """Verify that citations to non-retrieved chunks are rejected."""

    answer = "This statement cites 【Document 7, Chunk 999】"

    result = validate_citations(answer, retrieved_chunks)

    assert result["is_valid"] is False
    assert result["invalid_sources"] == [
        {"document_id": 7, "chunk_id": 999}
    ]


def test_answer_without_citations(retrieved_chunks):
    """Verify that answers without citations are not marked valid."""

    answer = "A fair trial protects individual rights and promotes justice."

    result = validate_citations(answer, retrieved_chunks)

    assert result["is_valid"] is False
    assert result["cited_sources"] == []
    assert result["invalid_sources"] == []


def test_mixed_valid_and_invalid_citations(retrieved_chunks):
    """Verify that an invalid citation causes validation to fail."""

    answer = """
    Fair trial protects individual rights.
    【Document 7, Chunk 59】

    Another statement cites an unavailable source.
    【Document 7, Chunk 999】
    """

    result = validate_citations(answer, retrieved_chunks)

    assert result["is_valid"] is False
    assert result["invalid_sources"] == [
        {"document_id": 7, "chunk_id": 999}
    ]


def test_answer_question_maps_only_cited_sources(monkeypatch):
    """Verify citation mapping and session-scoped semantic retrieval."""

    # Simulate chunks returned by semantic search.
    retrieved_chunks = [
        {
            "document_id": 7,
            "filename": "case 01.PDF",
            "chunk_id": 59,
            "chunk_index": 57,
            "chunk_text": "Source passage for chunk 59.",
            "distance": 0.12,
        },
        {
            "document_id": 7,
            "filename": "case 01.PDF",
            "chunk_id": 75,
            "chunk_index": 73,
            "chunk_text": "Source passage for chunk 75.",
            "distance": 0.18,
        },
    ]

    # Record the arguments passed to semantic search.
    search_calls = []

    def mock_search(embedding, session_id, limit=5):
        """Return sample chunks and record the requested session."""

        search_calls.append(
            {
                "embedding": embedding,
                "session_id": session_id,
                "limit": limit,
            }
        )
        return retrieved_chunks

    # Mock external dependencies to avoid real model or database calls.
    monkeypatch.setattr(
        "backend.services.rag.generate_embedding",
        lambda question: [0.01] * 384,
    )

    monkeypatch.setattr(
        "backend.services.rag.search_similar_chunks",
        mock_search,
    )

    monkeypatch.setattr(
        "backend.services.rag.generate_response",
        lambda prompt: (
            "A fair trial protects individual rights. "
            "【Document 7, Chunk 59】"
        ),
    )

    # Execute the RAG pipeline for a specific session.
    session_id = 999

    result = answer_question(
        "What is a fair trial?",
        session_id=session_id,
    )

    # Verify that semantic search received the correct session ID.
    assert len(search_calls) == 1
    assert search_calls[0]["session_id"] == session_id
    assert search_calls[0]["limit"] == 5

    # Both chunks should remain in the retrieved sources.
    assert len(result["sources"]) == 2

    # Only the chunk cited by the generated answer should be mapped.
    assert len(result["cited_source_details"]) == 1
    assert result["cited_source_details"][0]["chunk_id"] == 59

    # Verify that the mapped source retains its original metadata.
    assert result["cited_source_details"][0]["filename"] == "case 01.PDF"
    assert result["cited_source_details"][0]["chunk_index"] == 57
    assert result["cited_source_details"][0]["chunk_text"] == (
        "Source passage for chunk 59."
    )

    # The citation should pass source-membership validation.
    assert result["citation_validation"]["is_valid"] is True
