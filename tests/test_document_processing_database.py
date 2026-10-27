
"""Tests for document processing database operations."""

from unittest.mock import MagicMock, patch

import pytest

from backend.database import save_extracted_text, update_document_status
from backend.services.document_processing import chunk_text, save_document_chunks

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


# Test that saving chunks replaces old chunks and inserts new ones in order.
@patch("backend.database.psycopg.connect")
def test_save_document_chunks_replaces_existing_chunks(mock_connect):
    """Chunk replacement should delete old rows and insert indexed chunks."""
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Import the function here; we'll implement it after these tests are ready.
    from backend.database import save_document_chunks

    save_document_chunks(7, ["First chunk", "Second chunk", "Third chunk"])

    # The first query clears the old chunks for this document.
    delete_query, delete_parameters = cursor.execute.call_args_list[0].args
    assert "DELETE FROM document_chunks" in delete_query
    assert delete_parameters == (7,)

    # New chunks should be inserted in order, using zero-based indexes.
    insert_query, insert_rows = cursor.executemany.call_args.args
    assert "INSERT INTO document_chunks" in insert_query
    assert insert_rows == [
        (7, 0, "First chunk"),
        (7, 1, "Second chunk"),
        (7, 2, "Third chunk"),
    ]


def test_save_document_chunks_rejects_empty_chunks():
    """Empty input should not erase chunks already stored for a document."""
    from backend.database import save_document_chunks

    # Reject the input before opening a database connection.
    with patch("backend.database.psycopg.connect") as mock_connect:
        with pytest.raises(ValueError, match="at least one chunk"):
            save_document_chunks(7, [])

        mock_connect.assert_not_called()



@patch("backend.database.psycopg.connect")
def test_save_document_chunks_rolls_back_when_insert_fails(mock_connect):
    """A failed replacement should roll back instead of committing partial data."""
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Simulate a database error while inserting replacement chunks.
    cursor.executemany.side_effect = RuntimeError("Insert failed")

    from backend.database import save_document_chunks

    # The database error should propagate to the caller.
    with pytest.raises(RuntimeError, match="Insert failed"):
        save_document_chunks(7, ["Replacement chunk"])

    # An exception inside the connection context should trigger rollback.
    connection.__exit__.assert_called_once()
    assert connection.__exit__.call_args.args[0] is RuntimeError
