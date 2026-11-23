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




def _remove_session_files(
    session_id: int,
    documents: list[dict],
) -> None:
    """Remove uploaded files and the storage directory for one session."""

    # Build the storage directory belonging to this session.
    session_storage_dir = (STORAGE_DIR / str(session_id)).resolve()

    # Ensure the directory cannot escape the main storage directory.
    if session_storage_dir.parent != STORAGE_DIR:
        logger.error(
            "Unsafe session storage directory: %s",
            session_storage_dir,
        )
        return

    # Remove only files registered to this session.
    for document in documents:
        content_hash = document["content_hash"]
        file_type = document["file_type"]

        if not content_hash or not file_type:
            continue

        # Reconstruct the expected uploaded file path.
        extension = f".{file_type.lower()}"
        file_path = (
            session_storage_dir / f"{content_hash}{extension}"
        ).resolve()

        # Prevent deletion of files outside this session directory.
        if file_path.parent != session_storage_dir:
            logger.warning("Skipping unsafe storage path: %s", file_path)
            continue

        try:
            file_path.unlink(missing_ok=True)
        except OSError:
            logger.exception(
                "Could not remove session file: %s",
                file_path,
            )

    # Remove the session directory when it is empty.
    try:
        session_storage_dir.rmdir()
    except FileNotFoundError:
        pass
    except OSError:
        logger.warning(
            "Session storage directory could not be removed: %s",
            session_storage_dir,
        )


def end_session(session_id: int) -> bool:
    """Delete a session, its database records, and uploaded files."""

    # Delete database records and retrieve file metadata atomically.
    deleted_session = delete_session(session_id)

    if deleted_session is None:
        return False

    # Reuse the shared physical-file cleanup implementation.
    _remove_session_files(
        session_id,
        deleted_session["documents"],
    )

    return True


def end_expired_session(session_id: int) -> bool:
    """Delete a session only if it is still expired."""

    # Recheck expiry while acquiring the database session row lock.
    deleted_session = delete_session(
        session_id,
        only_if_expired=True,
    )

    if deleted_session is None:
        return False

    # Remove the physical files belonging to the expired session.
    _remove_session_files(
        session_id,
        deleted_session["documents"],
    )

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