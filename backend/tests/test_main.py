
"""Tests for the FastAPI application and question endpoints."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.sessions import get_authenticated_session


# Use FastAPI's test client without starting a live server.
client = TestClient(app)

# Simulate an authenticated session for question endpoint tests.
TEST_SESSION = {
    "id": 999,
    "created_at": "2026-01-01T10:00:00",
    "last_activity_at": "2026-01-01T10:00:00",
}


@pytest.fixture(autouse=True)
def authenticate_test_session():
    """Override authentication while running tests in this module."""

    app.dependency_overrides[get_authenticated_session] = (
        lambda: TEST_SESSION
    )

    yield

    # Prevent this override from leaking into other test modules.
    app.dependency_overrides.pop(get_authenticated_session, None)


def test_root_endpoint():
    """The root endpoint should return the API welcome message."""

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "AI Document Intelligence API is running"
    }


def test_health_endpoint():
    """The health endpoint should report a healthy application."""

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_valid_question():
    """A valid question should be accepted for the active session."""

    response = client.post(
        "/questions/preview",
        json={"question": "Summarize this document"},
    )

    assert response.status_code == 200
    assert response.json()["received_question"] == (
        "Summarize this document"
    )
    assert response.json()["session_id"] == TEST_SESSION["id"]


@patch("backend.routers.questions.save_conversation_turn")
@patch("backend.routers.questions.answer_question")
def test_ask_question(mock_answer_question, mock_save_conversation):
    """Verify RAG generation and conversation persistence."""

    # Simulate the response returned by the RAG pipeline.
    rag_result = {
        "question": "What is the main argument?",
        "answer": "The main argument concerns fair trial rights.",
        "sources": [{"document_id": 7, "chunk_id": 59}],
        "cited_source_details": [
            {"document_id": 7, "chunk_id": 59}
        ],
        "result_count": 1,
        "citation_validation": {
            "is_valid": True,
            "cited_sources": [
                {"document_id": 7, "chunk_id": 59}
            ],
            "invalid_sources": [],
        },
    }

    mock_answer_question.return_value = rag_result

    # Simulate the database record created by persistence.
    mock_save_conversation.return_value = {
        "id": 15,
        "created_at": "2026-11-12T10:00:00",
    }

    # Submit a question through the authenticated API endpoint.
    response = client.post(
        "/questions/ask",
        json={"question": "What is the main argument?"},
    )

    # Verify the API returns the generated answer and saved record ID.
    assert response.status_code == 200

    response_data = response.json()

    assert response_data["answer"] == (
        "The main argument concerns fair trial rights."
    )
    assert response_data["conversation_id"] == 15
    assert response_data["created_at"] == "2026-11-12T10:00:00"

    # Verify that RAG received the authenticated session ID.
    mock_answer_question.assert_called_once_with(
        "What is the main argument?",
        session_id=TEST_SESSION["id"],
    )

    # Verify that the generated response was persisted.
    mock_save_conversation.assert_called_once_with(
        session_id=TEST_SESSION["id"],
        question=rag_result["question"],
        answer=rag_result["answer"],
        sources=rag_result["sources"],
        cited_source_details=rag_result["cited_source_details"],
        citation_validation=rag_result["citation_validation"],
        result_count=rag_result["result_count"],
    )


@patch("backend.routers.questions.save_conversation_turn")
@patch("backend.routers.questions.answer_question")
def test_ask_question_database_failure(
    mock_answer_question,
    mock_save_conversation,
):
    """Verify database failures return a safe API error."""

    # Simulate successful answer generation.
    mock_answer_question.return_value = {
        "question": "What is a fair trial?",
        "answer": "A fair trial protects individual rights.",
        "sources": [],
        "cited_source_details": [],
        "result_count": 0,
        "citation_validation": {
            "is_valid": False,
            "cited_sources": [],
            "invalid_sources": [],
        },
    }

    # Simulate a PostgreSQL persistence failure.
    mock_save_conversation.side_effect = Exception(
        "Simulated database failure"
    )

    response = client.post(
        "/questions/ask",
        json={"question": "What is a fair trial?"},
    )

    assert response.status_code == 500
    assert response.json() == {
        "detail": "Unable to process your question at this time."
    }


@patch("backend.routers.questions.get_conversation_history")
def test_get_question_history(mock_get_history):
    """Verify history retrieval is restricted to the active session."""

    # Simulate previously saved conversations.
    expected_history = [
        {
            "id": 15,
            "question": "What is a fair trial?",
            "answer": "A fair trial protects individual rights.",
            "sources": [],
            "cited_source_details": [],
            "citation_validation": {"is_valid": True},
            "result_count": 2,
            "created_at": "2026-11-12T10:00:00",
        }
    ]

    mock_get_history.return_value = expected_history

    response = client.get("/questions/history")

    assert response.status_code == 200
    assert response.json() == {
        "history": expected_history,
        "count": 1,
    }

    # Ensure history is fetched using the authenticated session ID.
    mock_get_history.assert_called_once_with(TEST_SESSION["id"])


@patch("backend.routers.questions.get_conversation_history")
def test_get_question_history_empty(mock_get_history):
    """An active session without conversations should return empty history."""

    mock_get_history.return_value = []

    response = client.get("/questions/history")

    assert response.status_code == 200
    assert response.json() == {
        "history": [],
        "count": 0,
    }

    mock_get_history.assert_called_once_with(TEST_SESSION["id"])


@patch("backend.routers.questions.get_conversation_history")
def test_get_question_history_database_failure(mock_get_history):
    """Verify history database failures return a safe API error."""

    mock_get_history.side_effect = Exception(
        "Simulated database failure"
    )

    response = client.get("/questions/history")

    assert response.status_code == 500
    assert response.json() == {
        "detail": (
            "Unable to retrieve conversation history at this time."
        )
    }


def test_short_question_is_rejected():
    """Questions shorter than three characters should be rejected."""

    response = client.post(
        "/questions/preview",
        json={"question": "Hi"},
    )

    assert response.status_code == 422


def test_missing_question_is_rejected():
    """A missing question should fail request validation."""

    response = client.post(
        "/questions/preview",
        json={},
    )

    assert response.status_code == 422
