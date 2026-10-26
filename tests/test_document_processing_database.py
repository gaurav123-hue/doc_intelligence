
"""Tests for document processing database operations."""

from unittest.mock import MagicMock, patch

import pytest

from backend.database import save_extracted_text, update_document_status


@patch("backend.database.psycopg.connect")
def test_save_extracted_text_uses_upsert(mock_connect):
    """Saving extracted text should insert or update content safely."""
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    save_extracted_text(7, "Extracted document text")

    # Confirm that the query targets the content table and receives safe parameters.
    query, parameters = cursor.execute.call_args.args
    assert "INSERT INTO document_contents" in query
    assert "ON CONFLICT (document_id)" in query
    assert parameters == (7, "Extracted document text")


@patch("backend.database.psycopg.connect")
def test_update_document_status(mock_connect):
    """Updating status should target the requested document ID."""
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 1

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    update_document_status(7, "processed")

    query, parameters = cursor.execute.call_args.args
    assert "UPDATE documents" in query
    assert parameters == ("processed", 7)


@patch("backend.database.psycopg.connect")
def test_update_document_status_rejects_missing_document(mock_connect):
    """A missing document should not silently appear to update successfully."""
    connection = MagicMock()
    cursor = MagicMock()
    cursor.rowcount = 0

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    with pytest.raises(ValueError, match="does not exist"):
        update_document_status(999999, "processed")
