
"""Tests for document text chunking."""

import pytest

from backend.services.text_chunking import chunk_text


def test_short_text_returns_one_chunk():
    # Short text should not be split unnecessarily.
    assert chunk_text("Hello document") == ["Hello document"]


def test_long_text_is_split_with_overlap():
    # Small settings make the chunk boundaries easy to verify.
    chunks = chunk_text("abcdefghijkl", chunk_size=6, overlap=2)

    assert chunks == ["abcdef", "efghij", "ijkl"]


def test_empty_text_returns_no_chunks():
    # Empty or whitespace-only input has nothing to index.
    assert chunk_text("   \n  ") == []


def test_invalid_chunk_size_raises_error():
    # A zero-sized chunk would prevent the algorithm from progressing.
    with pytest.raises(ValueError, match="chunk_size"):
        chunk_text("some text", chunk_size=0)


def test_overlap_must_be_smaller_than_chunk_size():
    # Overlap equal to the chunk size would make the step zero.
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("some text", chunk_size=5, overlap=5)


def test_chunks_do_not_exceed_configured_size():
    # Every returned chunk must respect the configured limit.
    chunks = chunk_text("abcdefghijklmnopqrstuvwxyz", chunk_size=8, overlap=2)

    assert all(len(chunk) <= 8 for chunk in chunks)



def test_negative_overlap_raises_error():
    # Negative overlap is invalid because overlap must be zero or greater.
    with pytest.raises(ValueError, match="overlap"):
        chunk_text("some text", chunk_size=5, overlap=-1)
