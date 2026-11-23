
from unittest.mock import MagicMock, patch

from backend.database import (
    check_database_connection,
    create_document,
    get_documents,
    save_conversation_turn,
    get_conversation_history,
    delete_session,
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
    """Documents should be retrieved only for the requested session."""

    # Arrange: create a mocked database connection and cursor.
    mock_connection = MagicMock()
    mock_cursor = MagicMock()

    mock_connect.return_value = mock_connection
    mock_connection.__enter__.return_value = mock_connection
    mock_connection.cursor.return_value.__enter__.return_value = mock_cursor

    # Simulate documents belonging to the requested session.
    mock_cursor.fetchall.return_value = [
        (1, "annual_report.pdf", "PDF", "pending", None),
        (2, "meeting_notes.txt", "TXT", "pending", None),
    ]

    # Act: retrieve documents for session 999.
    result = get_documents(session_id=999)

    # Assert: verify the returned documents.
    assert len(result) == 2
    assert result[0]["filename"] == "annual_report.pdf"
    assert result[1]["filename"] == "meeting_notes.txt"
    assert result[0]["status"] == "pending"

    # Verify the query filters documents by session ID.
    mock_cursor.execute.assert_called_once()

    sql, parameters = mock_cursor.execute.call_args.args

    assert "SELECT" in sql
    assert "FROM documents" in sql
    assert "WHERE session_id = %s" in sql
    assert parameters == (999,)




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
    """Search should return ranked chunks from the requested session only."""

    # Arrange: create a mocked database connection and cursor.
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Simulate one matching chunk belonging to the requested session.
    cursor.fetchall.return_value = [
        (12, 7, "case 01.PDF", 3, "The court examined the investigation.", 0.12)
    ]

    # Act: search using a sample embedding and session ID.
    query_embedding = [0.01] * 384
    session_id = 999

    results = search_similar_chunks(
        query_embedding,
        session_id=session_id,
        limit=5,
    )

    # Assert: verify all returned fields.
    assert len(results) == 1
    assert results[0]["chunk_id"] == 12
    assert results[0]["document_id"] == 7
    assert results[0]["filename"] == "case 01.PDF"
    assert results[0]["chunk_index"] == 3
    assert results[0]["chunk_text"] == (
        "The court examined the investigation."
    )
    assert results[0]["distance"] == 0.12

    # Verify the SQL filters documents by session ID.
    sql, parameters = cursor.execute.call_args.args

    assert "<=>" in sql
    assert "JOIN documents" in sql
    assert "d.session_id = %s" in sql
    assert "ORDER BY" in sql
    assert "LIMIT" in sql

    assert parameters == (
        str(query_embedding),
        session_id,
        str(query_embedding),
        5,
    )



@patch("backend.database.psycopg.connect")
def test_save_conversation_turn(mock_connect):
    """Saving a conversation should persist its answer and metadata."""

    # Arrange: configure the mocked database connection.
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    cursor.fetchone.return_value = (15, None)

    sources = [{"document_id": 7, "chunk_id": 59}]
    cited_sources = [{"document_id": 7, "chunk_id": 59}]
    citation_validation = {
        "is_valid": True,
        "cited_sources": cited_sources,
        "invalid_sources": [],
    }

    # Act: save one conversation turn.
    result = save_conversation_turn(
        session_id=999,
        question="What is a fair trial?",
        answer="A fair trial protects individual rights.",
        sources=sources,
        cited_source_details=cited_sources,
        citation_validation=citation_validation,
        result_count=1,
    )

    # Assert: verify the generated database record.
    assert result["id"] == 15
    assert result["created_at"] is None

    # Verify that the INSERT targets the correct table.
    sql, parameters = cursor.execute.call_args.args

    assert "INSERT INTO conversation_turns" in sql
    assert "session_id" in sql
    assert "question" in sql
    assert "answer" in sql
    assert "sources" in sql
    assert "citation_validation" in sql

    # Verify the session and question are passed correctly.
    assert parameters[0] == 999
    assert parameters[1] == "What is a fair trial?"
    assert parameters[2] == "A fair trial protects individual rights."
    assert parameters[6] == 1


@patch("backend.database.psycopg.connect")
def test_get_conversation_history(mock_connect):
    """Conversation history should only include the requested session."""

    # Arrange: configure the mocked database connection.
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Simulate one previously saved conversation turn.
    cursor.fetchall.return_value = [
        (
            15,
            "What is a fair trial?",
            "A fair trial protects individual rights.",
            [{"document_id": 7, "chunk_id": 59}],
            [{"document_id": 7, "chunk_id": 59}],
            {
                "is_valid": True,
                "cited_sources": [
                    {"document_id": 7, "chunk_id": 59}
                ],
                "invalid_sources": [],
            },
            1,
            None,
        )
    ]

    # Act: retrieve history for session 999.
    result = get_conversation_history(session_id=999)

    # Assert: verify the returned conversation.
    assert len(result) == 1
    assert result[0]["id"] == 15
    assert result[0]["question"] == "What is a fair trial?"
    assert result[0]["answer"] == (
        "A fair trial protects individual rights."
    )
    assert result[0]["result_count"] == 1
    assert result[0]["citation_validation"]["is_valid"] is True

    # Verify that the query filters history by session ID.
    sql, parameters = cursor.execute.call_args.args

    assert "FROM conversation_turns" in sql
    assert "WHERE session_id = %s" in sql
    assert "ORDER BY created_at ASC" in sql
    assert parameters == (999,)



@patch("backend.database.psycopg.connect")
def test_delete_session_returns_document_metadata(mock_connect):
    """Deleting a session should return metadata for its uploaded files."""

    # Arrange: configure the mocked database connection and cursor.
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Simulate an existing session.
    cursor.fetchone.side_effect = [
        (999,),  # Session found by SELECT ... FOR UPDATE.
        (999,),  # Session deleted successfully.
    ]

    # Simulate two documents belonging to the session.
    cursor.fetchall.return_value = [
        (1, "report.pdf", "PDF", "abc123"),
        (2, "notes.txt", "TXT", "def456"),
    ]

    # Act: delete session 999.
    result = delete_session(session_id=999)

    # Assert: verify the returned session metadata.
    assert result["session_id"] == 999 # type: ignore
    assert len(result["documents"]) == 2 # type: ignore
    assert result["documents"][0]["filename"] == "report.pdf" # type: ignore
    assert result["documents"][0]["content_hash"] == "abc123" # type: ignore
    assert result["documents"][1]["filename"] == "notes.txt" # type: ignore
    assert result["documents"][1]["content_hash"] == "def456" # type: ignore

    # Verify that the session row was locked before deletion.
    executed_queries = [
        call.args[0] for call in cursor.execute.call_args_list
    ]

    assert "FOR UPDATE" in executed_queries[0]
    assert "FROM documents" in executed_queries[1]
    assert "DELETE FROM sessions" in executed_queries[2]


@patch("backend.database.psycopg.connect")
def test_delete_session_returns_none_when_missing(mock_connect):
    """Deleting a nonexistent session should return None."""

    # Arrange: configure the mocked database connection.
    connection = MagicMock()
    cursor = MagicMock()

    mock_connect.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    # Simulate a session that does not exist.
    cursor.fetchone.return_value = None

    # Act: attempt to delete the nonexistent session.
    result = delete_session(session_id=999999)

    # Assert: no session should be returned or deleted.
    assert result is None

    # Verify that only the session lookup was executed.
    cursor.execute.assert_called_once()

    sql = cursor.execute.call_args.args[0]
    assert "FOR UPDATE" in sql
    