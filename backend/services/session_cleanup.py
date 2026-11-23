
"""Background service for automatically cleaning up expired sessions."""

import asyncio
import logging

from backend.database import get_expired_session_ids
from backend.services.sessions import end_expired_session

# Use Uvicorn's configured logger so worker messages appear in the terminal.
logger = logging.getLogger("uvicorn.error")

# Check for expired sessions every 60 seconds.
CLEANUP_INTERVAL_SECONDS = 60


def cleanup_expired_sessions() -> int:
    """Delete all sessions that have exceeded the inactivity limit."""

    # Find sessions that appear to have exceeded 60 minutes of inactivity.
    expired_session_ids = get_expired_session_ids()

    deleted_count = 0

    # Recheck expiry atomically before deleting each candidate session.
    for session_id in expired_session_ids:
        try:
            if end_expired_session(session_id):
                deleted_count += 1
                logger.info(
                    "Automatically cleaned up expired session %s",
                    session_id,
                )

        except Exception:
            # One failed cleanup must not prevent other sessions being processed.
            logger.exception(
                "Failed to clean up expired session %s",
                session_id,
            )

    if deleted_count:
        logger.info(
            "Expired session cleanup completed. Deleted %s session(s).",
            deleted_count,
        )

    return deleted_count


async def session_cleanup_worker() -> None:
    """Periodically clean up expired sessions in the background."""

    logger.info("Session cleanup background worker started.")

    while True:
        try:
            # Run blocking database and filesystem operations outside the event loop.
            await asyncio.to_thread(cleanup_expired_sessions)

        except asyncio.CancelledError:
            # Allow FastAPI shutdown to stop the background worker cleanly.
            raise

        except Exception:
            logger.exception("Unexpected error in session cleanup worker.")

        # Wait before checking for expired sessions again.
        await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
