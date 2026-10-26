
"""Tests for document upload validation and duplicate detection."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app

# Use FastAPI's test client so tests can exercise routes without a live server.
client = TestClient(app)



@patch("backend.routers.documents.create_uploaded_document")
@patch("backend.routers.documents.get_document_by_hash")
def test_upload_success(
    mock_get_by_hash,
    mock_create,
    tmp_path,
    monkeypatch,
):
    """A valid upload should create a record in isolated test storage."""

    # Redirect file storage to a temporary directory instead of real storage.
    monkeypatch.setattr(
        "backend.routers.documents.STORAGE_DIR",
        tmp_path,
    )

    # Simulate a file whose contents have not been uploaded before.
    mock_get_by_hash.return_value = None

    # Simulate the metadata returned by a successful database insertion.
    mock_create.return_value = {
        "id": 100,
        "filename": "test.txt",
        "file_type": "TXT",
        "status": "pending",
        "created_at": "2026-01-01T10:00:00",
    }

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "test.txt",
                b"sample document content",
                "text/plain",
            )
        },
    )

    assert response.status_code == 201
    assert response.json()["filename"] == "test.txt"
    mock_create.assert_called_once()

    # Verify that the uploaded file was written to temporary storage.
    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == b"sample document content"



@patch("backend.routers.documents.get_document_by_hash")
def test_upload_duplicate_content_returns_conflict(mock_get_by_hash):
    """Identical content should return HTTP 409."""

    # Simulate a matching document already stored in the database.
    mock_get_by_hash.return_value = {"id": 12}

    response = client.post(
        "/documents/upload",
        files={"file": ("copy.txt", b"already stored content", "text/plain")},
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_upload_rejects_unsupported_extension():
    """Unsupported extensions should be rejected before storage."""

    response = client.post(
        "/documents/upload",
        files={"file": ("script.exe", b"not an allowed document", "application/octet-stream")},
    )

    assert response.status_code == 400


def test_upload_rejects_empty_file():
    """An empty upload should not create a document."""

    response = client.post(
        "/documents/upload",
        files={"file": ("empty.txt", b"", "text/plain")},
    )

    assert response.status_code == 400


@patch("backend.routers.documents.get_document_by_hash")
def test_upload_rejects_file_over_size_limit(mock_get_by_hash):
    """Files larger than the configured limit should be rejected."""

    # This creates 10 MB plus one byte to exceed the current limit.
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/documents/upload",
        files={"file": ("large.txt", oversized_content, "text/plain")},
    )

    assert response.status_code == 413

    # Hash lookup must not run for an oversized file.
    mock_get_by_hash.assert_not_called()




@patch("backend.routers.documents.create_uploaded_document")
@patch("backend.routers.documents.get_document_by_hash")
def test_upload_cleans_up_file_when_database_insert_fails(
    mock_get_by_hash,
    mock_create,
    tmp_path,
    monkeypatch,
):
    """A failed database insert should not leave an orphaned file."""

    # Keep this test isolated from the application's real storage directory.
    monkeypatch.setattr(
        "backend.routers.documents.STORAGE_DIR",
        tmp_path,
    )

    # Pretend this document is new, but make the database insert fail.
    mock_get_by_hash.return_value = None
    mock_create.side_effect = RuntimeError("Simulated database failure")

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "failure_test.txt",
                b"content for the failure test",
                "text/plain",
            )
        },
    )

    # The API should report an internal error without exposing database details.
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to save uploaded document"

    # No file should remain after the failed insertion.
    assert list(tmp_path.iterdir()) == []
