from fastapi.testclient import TestClient

from backend.main import app

client = TestClient(app)


def test_root_endpoint():
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {
        "message": "AI Document Intelligence API is running"
    }


def test_health_endpoint():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_valid_question():
    response = client.post(
        "/questions/preview",
        json={"question": "Summarize this document"},
    )

    assert response.status_code == 200
    assert response.json()["received_question"] == (
        "Summarize this document"
    )


def test_short_question_is_rejected():
    response = client.post(
        "/questions/preview",
        json={"question": "Hi"},
    )

    assert response.status_code == 422


def test_missing_question_is_rejected():
    response = client.post(
        "/questions/preview",
        json={},
    )

    assert response.status_code == 422