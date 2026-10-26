
"""Tests for coordinating document extraction and persistence."""

from unittest.mock import patch

import pytest

from backend.services.document_processing import process_document
from backend.services.text_extraction import TextExtractionError


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_saves_text_then_marks_processed(
    mock_extract,
    mock_save,
    mock_update_status,
):
    """Successful extraction should save text before marking success."""
    mock_extract.return_value = "Extracted document content"

    process_document(12, "storage/documents/example.txt")

    mock_extract.assert_called_once()
    mock_save.assert_called_once_with(12, "Extracted document content")
    mock_update_status.assert_called_once_with(12, "processed")


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_marks_failed_when_extraction_fails(
    mock_extract,
    mock_save,
    mock_update_status,
):
    """Extraction errors should mark the document failed and propagate."""
    mock_extract.side_effect = TextExtractionError("No extractable text")

    with pytest.raises(TextExtractionError, match="No extractable text"):
        process_document(12, "storage/documents/example.txt")

    mock_save.assert_not_called()
    mock_update_status.assert_called_once_with(12, "failed")


@patch("backend.services.document_processing.update_document_status")
@patch("backend.services.document_processing.save_extracted_text")
@patch("backend.services.document_processing.extract_text")
def test_process_document_marks_failed_when_saving_text_fails(
    mock_extract,
    mock_save,
    mock_update_status,
):
    """A content persistence failure should not mark the document processed."""
    mock_extract.return_value = "Extracted document content"
    mock_save.side_effect = RuntimeError("Database write failed")

    with pytest.raises(RuntimeError, match="Database write failed"):
        process_document(12, "storage/documents/example.txt")

    # The first status update records failure; processed must never be written.
    mock_update_status.assert_called_once_with(12, "failed")
