
"""Tests for document upload validation, duplicate detection, and processing."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app

# Use FastAPI's test client to exercise routes without starting a live server.
client = TestClient(app)


@patch("backend.routers.documents.process_document")
@patch("backend.routers.documents.create_uploaded_document")
@patch("backend.routers.documents.get_document_by_hash")
def test_upload_success(
    mock_get_by_hash,
    mock_create,
    mock_process,
    tmp_path,
    monkeypatch,
):
    """A valid upload should save the file and process its contents."""

    # Keep this test isolated from real application storage.
    monkeypatch.setattr("backend.routers.documents.STORAGE_DIR", tmp_path)

    # Simulate content that has not previously been uploaded.
    mock_get_by_hash.return_value = None

    # Simulate a successful metadata insertion.
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

    # The route should return created metadata with the final processing status.
    assert response.status_code == 201
    assert response.json()["filename"] == "test.txt"
    assert response.json()["status"] == "processed"

    # Confirm metadata creation and document processing were each attempted once.
    mock_create.assert_called_once()
    mock_process.assert_called_once()

    # Verify the uploaded bytes were stored without modification.
    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == b"sample document content"


@patch("backend.routers.documents.process_document")
@patch("backend.routers.documents.create_uploaded_document")
@patch("backend.routers.documents.get_document_by_hash")
def test_upload_keeps_file_when_processing_fails(
    mock_get_by_hash,
    mock_create,
    mock_process,
    tmp_path,
    monkeypatch,
):
    """A processing failure should preserve the file and metadata."""

    # Use temporary storage to avoid affecting real uploaded documents.
    monkeypatch.setattr("backend.routers.documents.STORAGE_DIR", tmp_path)

    # Simulate a new document whose metadata is saved successfully.
    mock_get_by_hash.return_value = None
    mock_create.return_value = {
        "id": 101,
        "filename": "processing_failure.txt",
        "file_type": "TXT",
        "status": "pending",
        "created_at": "2026-01-01T10:00:00",
    }

    # Simulate an extraction or persistence error.
    mock_process.side_effect = ValueError("Simulated processing failure")

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "processing_failure.txt",
                b"document content for processing failure",
                "text/plain",
            )
        },
    )

    # Upload succeeded even though subsequent processing failed.
    assert response.status_code == 201
    assert response.json()["id"] == 101
    assert response.json()["status"] == "failed"

    # Preserve the file for investigation or a future retry.
    stored_files = list(tmp_path.iterdir())
    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == (
        b"document content for processing failure"
    )

    # Confirm the processing service was invoked once.
    mock_process.assert_called_once()


@patch("backend.routers.documents.get_document_by_hash")
def test_upload_duplicate_content_returns_conflict(mock_get_by_hash):
    """Identical content should return HTTP 409."""

    # Simulate a matching document already recorded in the database.
    mock_get_by_hash.return_value = {"id": 12}

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "copy.txt",
                b"already stored content",
                "text/plain",
            )
        },
    )

    assert response.status_code == 409
    assert "already exists" in response.json()["detail"]


def test_upload_rejects_unsupported_extension():
    """Unsupported file extensions should be rejected."""

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "script.exe",
                b"not an allowed document",
                "application/octet-stream",
            )
        },
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

    # Create a payload one byte larger than the 10 MiB limit.
    oversized_content = b"x" * (10 * 1024 * 1024 + 1)

    response = client.post(
        "/documents/upload",
        files={
            "file": (
                "large.txt",
                oversized_content,
                "text/plain",
            )
        },
    )

    assert response.status_code == 413

    # Duplicate lookup should not run for an oversized upload.
    mock_get_by_hash.assert_not_called()


@patch("backend.routers.documents.create_uploaded_document")
@patch("backend.routers.documents.get_document_by_hash")
def test_upload_cleans_up_file_when_database_insert_fails(
    mock_get_by_hash,
    mock_create,
    tmp_path,
    monkeypatch,
):
    """A failed metadata insert should not leave an orphaned file."""

    # Isolate the test from the application's normal storage directory.
    monkeypatch.setattr("backend.routers.documents.STORAGE_DIR", tmp_path)

    # Simulate a new document whose metadata insertion fails.
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

    # Return a safe error message without exposing database internals.
    assert response.status_code == 500
    assert response.json()["detail"] == "Failed to save uploaded document"

    # The file created by this request should be removed.
    assert list(tmp_path.iterdir()) == []
