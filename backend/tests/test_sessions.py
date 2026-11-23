"""Tests for session lifecycle and uploaded-file cleanup."""

from unittest.mock import patch

from backend.services.sessions import end_session
from backend.services.sessions import end_expired_session

@patch("backend.services.sessions.delete_session")
def test_end_session_removes_uploaded_files(mock_delete_session, tmp_path):
    """Ending a session should remove its uploaded files and directory."""

    # Arrange: create a temporary storage directory for session 999.
    session_id = 999
    session_storage_dir = tmp_path / str(session_id)
    session_storage_dir.mkdir(parents=True)

    # Create two sample uploaded files.
    pdf_file = session_storage_dir / "abc123.pdf"
    txt_file = session_storage_dir / "def456.txt"

    pdf_file.write_text("Sample PDF placeholder")
    txt_file.write_text("Sample text document")

    # Mock the database deletion response.
    mock_delete_session.return_value = {
        "session_id": session_id,
        "documents": [
            {
                "id": 1,
                "filename": "report.pdf",
                "file_type": "PDF",
                "content_hash": "abc123",
            },
            {
                "id": 2,
                "filename": "notes.txt",
                "file_type": "TXT",
                "content_hash": "def456",
            },
        ],
    }

    # Redirect storage to pytest's temporary directory.
    with patch(
        "backend.services.sessions.STORAGE_DIR",
        tmp_path,
    ):
        # Act: end the session.
        result = end_session(session_id)

    # Assert: session deletion succeeded.
    assert result is True

    # Verify that both uploaded files were removed.
    assert not pdf_file.exists()
    assert not txt_file.exists()

    # Verify that the session directory was removed.
    assert not session_storage_dir.exists()

    # Verify that the database deletion was requested.
    mock_delete_session.assert_called_once_with(session_id)


@patch("backend.services.sessions.delete_session")
def test_end_session_returns_false_when_session_missing(
    mock_delete_session,
    tmp_path,
):
    """A missing session should not trigger filesystem cleanup."""

    # Arrange: simulate a session that does not exist.
    mock_delete_session.return_value = None

    # Create a separate directory to ensure it remains untouched.
    session_storage_dir = tmp_path / "999"
    session_storage_dir.mkdir()

    sample_file = session_storage_dir / "sample.pdf"
    sample_file.write_text("Sample document")

    # Act: attempt to end the nonexistent session.
    with patch(
        "backend.services.sessions.STORAGE_DIR",
        tmp_path,
    ):
        result = end_session(999)

    # Assert: deletion should report that the session was not found.
    assert result is False

    # Verify that unrelated filesystem data remains untouched.
    assert session_storage_dir.exists()
    assert sample_file.exists()

    mock_delete_session.assert_called_once_with(999)



@patch("backend.services.sessions.delete_session")
def test_end_session_does_not_delete_other_sessions_files(
    mock_delete_session,
    tmp_path,
):
    """Ending one session must not affect another session's files."""

    # Arrange: create separate storage directories for two sessions.
    session_a = 999
    session_b = 1000

    session_a_dir = tmp_path / str(session_a)
    session_b_dir = tmp_path / str(session_b)

    session_a_dir.mkdir()
    session_b_dir.mkdir()

    # Create one uploaded file for each session.
    file_a = session_a_dir / "abc123.pdf"
    file_b = session_b_dir / "def456.txt"

    file_a.write_text("Session A document")
    file_b.write_text("Session B document")

    # Simulate deletion metadata for Session A only.
    mock_delete_session.return_value = {
        "session_id": session_a,
        "documents": [
            {
                "id": 1,
                "filename": "report.pdf",
                "file_type": "PDF",
                "content_hash": "abc123",
            }
        ],
    }

    # Act: terminate Session A.
    with patch(
        "backend.services.sessions.STORAGE_DIR",
        tmp_path,
    ):
        result = end_session(session_a)

    # Assert: Session A should be completely removed.
    assert result is True
    assert not file_a.exists()
    assert not session_a_dir.exists()

    # Session B must remain completely untouched.
    assert file_b.exists()
    assert session_b_dir.exists()
    assert file_b.read_text() == "Session B document"

    mock_delete_session.assert_called_once_with(session_a)


@patch("backend.services.sessions.delete_session")
def test_end_expired_session_removes_files_when_expired(
    mock_delete_session,
    tmp_path,
):
    """An expired session should have its files removed."""

    session_id = 2000
    session_storage_dir = tmp_path / str(session_id)
    session_storage_dir.mkdir()

    uploaded_file = session_storage_dir / "abc123.pdf"
    uploaded_file.write_text("Expired session document")

    # Simulate successful deletion of an expired database session.
    mock_delete_session.return_value = {
        "session_id": session_id,
        "documents": [
            {
                "id": 1,
                "filename": "report.pdf",
                "file_type": "PDF",
                "content_hash": "abc123",
            }
        ],
    }

    with patch("backend.services.sessions.STORAGE_DIR", tmp_path):
        result = end_expired_session(session_id)

    assert result is True
    assert not uploaded_file.exists()
    assert not session_storage_dir.exists()

    # Ensure expiry was rechecked by the database deletion function.
    mock_delete_session.assert_called_once_with(
        session_id,
        only_if_expired=True,
    )


@patch("backend.services.sessions.delete_session")
def test_end_expired_session_preserves_refreshed_session_files(
    mock_delete_session,
    tmp_path,
):
    """A session refreshed before deletion must retain its files."""

    session_id = 2001
    session_storage_dir = tmp_path / str(session_id)
    session_storage_dir.mkdir()

    uploaded_file = session_storage_dir / "abc123.pdf"
    uploaded_file.write_text("Active session document")

    # Simulate the database rejecting deletion because the session is active.
    mock_delete_session.return_value = None

    with patch("backend.services.sessions.STORAGE_DIR", tmp_path):
        result = end_expired_session(session_id)

    assert result is False
    assert uploaded_file.exists()
    assert session_storage_dir.exists()

    mock_delete_session.assert_called_once_with(
        session_id,
        only_if_expired=True,
    )