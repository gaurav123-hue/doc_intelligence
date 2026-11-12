
"""Tests for coordinating document extraction, chunking, and persistence."""

from unittest.mock import patch
import pytest

from backend.services.document_processing import process_document
from backend.services.text_extraction import TextExtractionError


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_document_chunks")
@patch("backend.services.document_processing.chunk_text")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_saves_text_and_chunks_before_marking_processed(
    mock_extract,
    mock_save_text,
    mock_chunk_text,
    mock_save_chunks,
    mock_update_status,
):
    """Save the full text and its chunks before marking processing successful."""
    mock_extract.return_value = "Extracted document content"
    mock_chunk_text.return_value = ["Extracted document", "document content"]

    process_document(12, "storage/documents/example.txt")

    # Verify extraction, full-text persistence, chunking, and chunk persistence.
    mock_extract.assert_called_once_with("storage/documents/example.txt")
    mock_save_text.assert_called_once_with(12, "Extracted document content")
    mock_chunk_text.assert_called_once_with("Extracted document content")
    mock_save_chunks.assert_called_once_with(
        12, ["Extracted document", "document content"]
    )

    # The processed status must be recorded only after all persistence succeeds.
    mock_update_status.assert_called_once_with(12, "processed")


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_document_chunks")
@patch("backend.services.document_processing.chunk_text")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_marks_failed_when_extraction_fails(
    mock_extract,
    mock_save_text,
    mock_chunk_text,
    mock_save_chunks,
    mock_update_status,
):
    """Extraction errors should mark the document failed and propagate."""
    mock_extract.side_effect = TextExtractionError("No extractable text")

    with pytest.raises(TextExtractionError, match="No extractable text"):
        process_document(12, "storage/documents/example.txt")

    # Later pipeline steps must not run when extraction fails.
    mock_save_text.assert_not_called()
    mock_chunk_text.assert_not_called()
    mock_save_chunks.assert_not_called()
    mock_update_status.assert_called_once_with(12, "failed")


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_document_chunks")
@patch("backend.services.document_processing.chunk_text")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_marks_failed_when_saving_text_fails(
    mock_extract,
    mock_save_text,
    mock_chunk_text,
    mock_save_chunks,
    mock_update_status,
):
    """A full-text persistence failure must prevent later processing steps."""
    mock_extract.return_value = "Extracted document content"
    mock_save_text.side_effect = RuntimeError("Database write failed")

    with pytest.raises(RuntimeError, match="Database write failed"):
        process_document(12, "storage/documents/example.txt")

    # Chunking and chunk persistence must not run after the text save fails.
    mock_chunk_text.assert_not_called()
    mock_save_chunks.assert_not_called()

    # The document must not be marked processed.
    mock_update_status.assert_called_once_with(12, "failed")


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_document_chunks")
@patch("backend.services.document_processing.chunk_text")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_marks_failed_when_saving_chunks_fails(
    mock_extract,
    mock_save_text,
    mock_chunk_text,
    mock_save_chunks,
    mock_update_status,
):
    """A chunk persistence failure must prevent the processed status."""
    mock_extract.return_value = "Extracted document content"
    mock_chunk_text.return_value = ["Extracted document content"]
    mock_save_chunks.side_effect = RuntimeError("Chunk insert failed")

    with pytest.raises(RuntimeError, match="Chunk insert failed"):
        process_document(12, "storage/documents/example.txt")

    # The full text and chunks are prepared, but the chunk save fails.
    mock_save_text.assert_called_once_with(12, "Extracted document content")
    mock_chunk_text.assert_called_once_with("Extracted document content")
    mock_save_chunks.assert_called_once_with(
        12, ["Extracted document content"]
    )

    # Failure is recorded; success must never be recorded.
    mock_update_status.assert_called_once_with(12, "failed")
