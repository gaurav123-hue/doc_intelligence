
"""Tests for session-aware document upload validation and processing."""

import pytest
from unittest.mock import patch

from fastapi.testclient import TestClient

from backend.main import app
from backend.services.sessions import get_authenticated_session


# Use FastAPI's test client without starting a live server.
client = TestClient(app)

# Provide a consistent authenticated session for upload tests.
TEST_SESSION = {
    "id": 999,
    "created_at": "2026-01-01T10:00:00",
    "last_activity_at": "2026-01-01T10:00:00",
}


@pytest.fixture(autouse=True)
def authenticate_test_session():
    """Override session authentication for every test in this module."""

    app.dependency_overrides[get_authenticated_session] = (
        lambda: TEST_SESSION
    )

    yield

    # Remove the override so it cannot affect other test modules.
    app.dependency_overrides.pop(get_authenticated_session, None)


def get_stored_files(storage_path):
    """Return all physical files, including files in session directories."""

    return [
        path
        for path in storage_path.rglob("*")
        if path.is_file()
    ]


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

    monkeypatch.setattr(
        "backend.routers.documents.STORAGE_DIR",
        tmp_path,
    )

    mock_get_by_hash.return_value = None

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
    assert response.json()["status"] == "processed"

    mock_get_by_hash.assert_called_once_with(
        mock_get_by_hash.call_args.args[0],
        TEST_SESSION["id"],
    )
    mock_create.assert_called_once()
    mock_process.assert_called_once()

    stored_files = get_stored_files(tmp_path)

    assert len(stored_files) == 1
    assert stored_files[0].parent.name == str(TEST_SESSION["id"])
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

    monkeypatch.setattr(
        "backend.routers.documents.STORAGE_DIR",
        tmp_path,
    )

    mock_get_by_hash.return_value = None

    mock_create.return_value = {
        "id": 101,
        "filename": "processing_failure.txt",
        "file_type": "TXT",
        "status": "pending",
        "created_at": "2026-01-01T10:00:00",
    }

    mock_process.side_effect = ValueError(
        "Simulated processing failure"
    )

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

    assert response.status_code == 201
    assert response.json()["id"] == 101
    assert response.json()["status"] == "failed"

    stored_files = get_stored_files(tmp_path)

    assert len(stored_files) == 1
    assert stored_files[0].read_bytes() == (
        b"document content for processing failure"
    )

    mock_process.assert_called_once()


@patch("backend.routers.documents.get_document_by_hash")
def test_upload_duplicate_content_returns_conflict(mock_get_by_hash):
    """Identical content should return HTTP 409."""

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
        files={
            "file": ("empty.txt", b"", "text/plain")
        },
    )

    assert response.status_code == 400


@patch("backend.routers.documents.get_document_by_hash")
def test_upload_rejects_file_over_size_limit(mock_get_by_hash):
    """Files larger than the configured limit should be rejected."""

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

    monkeypatch.setattr(
        "backend.routers.documents.STORAGE_DIR",
        tmp_path,
    )

    mock_get_by_hash.return_value = None

    mock_create.side_effect = RuntimeError(
        "Simulated database failure"
    )

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

    assert response.status_code == 500
    assert response.json()["detail"] == (
        "Failed to save uploaded document"
    )

    assert get_stored_files(tmp_path) == []
