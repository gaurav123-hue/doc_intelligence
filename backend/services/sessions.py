"""Business logic for secure session creation and validation."""
from fastapi import Header, HTTPException, status
import hashlib
import logging
from pathlib import Path
import secrets

from backend.database import (
    create_session,
    get_active_session,
    delete_session,
    get_session_documents
)

# Keep cleanup errors in server logs for troubleshooting.
logger = logging.getLogger(__name__)

# Resolve the document storage directory from the project root.
STORAGE_DIR = Path("storage/documents").resolve()

def generate_session_token() -> str:
    """Generate a cryptographically secure, unpredictable session token."""

    return secrets.token_urlsafe(32)

def hash_session_token(token: str) -> str:
    """Return the SHA-256 hash of a session token.

    Only this hash is stored in PostgreSQL, never the original token.
    """

    return hashlib.sha256(token.encode("utf-8")).hexdigest()

def start_session() -> dict:
    """Create a new session and return its ID and secret token."""

    token = generate_session_token()
    token_hash = hash_session_token(token)

    session = create_session(token_hash)

    # Return the raw token once so the client can authenticate future requests.
    return {
        "session_id": session["id"],
        "session_token": token,
        "created_at": session["created_at"],
        "last_activity_at": session["last_activity_at"],
    }

def validate_session(token: str) -> dict | None:
    """Validate a token and refresh activity for a non-expired session."""

    token_hash = hash_session_token(token)

    return get_active_session(token_hash)

def end_session(session_id: int) -> bool:
    """Delete a session, its database records, and uploaded files."""

    # Retrieve only documents owned by the session being terminated.
    documents = get_session_documents(session_id)

    # Reconstruct and validate each physical storage path.
    file_paths = []

    for document in documents:
        content_hash = document["content_hash"]
        file_type = document["file_type"]

        if not content_hash or not file_type:
            continue

        # The original upload process uses the lowercase extension.
        extension = f".{file_type.lower()}"
        file_path = (STORAGE_DIR / f"{content_hash}{extension}").resolve()

        # Prevent any path outside the document storage directory.
        if file_path.parent != STORAGE_DIR:
            logger.warning("Skipping unsafe storage path: %s", file_path)
            continue

        file_paths.append(file_path)

    # Delete the database session first. Foreign-key cascades remove
    # its documents, extracted contents, chunks, and conversation history.
    deleted = delete_session(session_id)

    if not deleted:
        return False

    # Remove physical files after the database transaction succeeds.
    for file_path in file_paths:
        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            # Log failures so orphaned files can be handled by cleanup later.
            logger.exception("Could not remove session file: %s", file_path)

    return True

def get_authenticated_session(
    authorization: str | None = Header(default=None),
) -> dict:
    """Authenticate a request and return its active session."""

    # Require a Bearer token in the Authorization header.
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

    return session