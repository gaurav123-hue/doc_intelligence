"""API endpoints for creating and validating workspace sessions."""

from fastapi import APIRouter, Header, HTTPException, status

from backend.services.sessions import (
    start_session,
    validate_session,
    end_session,
)

router = APIRouter(prefix="/sessions", tags=["Sessions"])


@router.post("/start", status_code=status.HTTP_201_CREATED)
def create_new_session():
    """Create a new workspace session."""

    return start_session()

@router.get("/me")
def get_current_session(
    authorization: str | None = Header(default=None),
):
    """Validate the session using its Bearer token."""

    # Require the standard Bearer authentication format.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid session token is required.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid session token is required.",
        )

    session = validate_session(token)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or has expired.",
        )

    return {
        "session_id": session["id"],
        "created_at": session["created_at"],
        "last_activity_at": session["last_activity_at"],
        "status": "active",
    }

@router.delete("/end")
def end_current_session(
    authorization: str | None = Header(default=None),
):
    """End the authenticated workspace session."""

    # Require a Bearer token to identify the session owner.
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid session token is required.",
        )

    token = authorization.removeprefix("Bearer ").strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="A valid session token is required.",
        )

    # Validate the session before attempting deletion.
    session = validate_session(token)

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session is invalid or has expired.",
        )

    # Delete only the authenticated user's session.
    deleted = end_session(session["id"])

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found.",
        )

    return {
        "message": "Session ended successfully.",
        "session_id": session["id"],
    }