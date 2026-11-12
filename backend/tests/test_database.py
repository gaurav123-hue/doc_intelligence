
from unittest.mock import MagicMock, patch

from backend.database import (
    check_database_connection,
    create_document,
    get_documents,
)

@patch("backend.database.psycopg.connect")
def test_check_database_connection(mock_connect):
    # Arrange
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_connection
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor
    mock_cursor.fetchone.return_value = (1,)

    # Act
    result = check_database_connection()

    # Assert
    assert result == 1
    mock_connect.assert_called_once()


@patch("backend.database.psycopg.connect")
def test_create_document(mock_connect):
    # Arrange
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_connection
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.fetchone.return_value = (
        2,
        "meeting_notes.txt",
        "TXT",
        "pending",
        None,
    )

    # Act
    result = create_document("meeting_notes.txt", "TXT")

    # Assert: returned document
    assert result["id"] == 2
    assert result["filename"] == "meeting_notes.txt"
    assert result["file_type"] == "TXT"
    assert result["status"] == "pending"
    assert result["created_at"] is None

    # Assert: SQL and parameterized values
    mock_cursor.execute.assert_called_once()
    sql, parameters = mock_cursor.execute.call_args.args

    assert "INSERT INTO documents" in sql
    assert "RETURNING" in sql
    assert parameters == ("meeting_notes.txt", "TXT")





@patch("backend.database.psycopg.connect")
def test_get_documents(mock_connect):
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_connection
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    mock_cursor.fetchall.return_value = [
        (1, "annual_report.pdf", "PDF", "pending", None),
        (2, "meeting_notes.txt", "TXT", "pending", None),
    ]

    result = get_documents()

    assert len(result) == 2
    assert result[0]["filename"] == "annual_report.pdf"
    assert result[1]["filename"] == "meeting_notes.txt"
    assert result[0]["status"] == "pending"

    mock_cursor.execute.assert_called_once()
    sql = mock_cursor.execute.call_args.args[0]
    assert "SELECT" in sql
    assert "FROM documents" in sql



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



from backend.database import search_similar_chunks



@patch("backend.database.psycopg.connect")
def test_search_similar_chunks_returns_ranked_results(mock_connect):
    """Search should return chunk details, filename, and cosine distance."""

    # Arrange: mock the database connection and its cursor.
    connection = MagicMock()
    cursor = MagicMock()
    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Simulate one matching chunk, including its parent document filename.
    cursor.fetchall.return_value = [
        (12, 7, "case 01.PDF", 3, "The court examined the investigation.", 0.12)
    ]

    # Act: search using a sample 384-dimensional query vector.
    query_embedding = [0.01] * 384
    results = search_similar_chunks(query_embedding, limit=5)

    # Assert: verify all returned fields match the database row.
    assert len(results) == 1
    assert results[0]["chunk_id"] == 12
    assert results[0]["document_id"] == 7
    assert results[0]["filename"] == "case 01.PDF"
    assert results[0]["chunk_index"] == 3
    assert results[0]["chunk_text"] == "The court examined the investigation."
    assert results[0]["distance"] == 0.12

    # Verify cosine distance is used and values are parameterized.
    sql, parameters = cursor.execute.call_args.args
    assert "<=>" in sql
    assert "JOIN documents" in sql
    assert "ORDER BY" in sql
    assert "LIMIT" in sql
    assert parameters == (str(query_embedding), str(query_embedding), 5)
