
"""Tests for the automatic expired-session cleanup service."""

from unittest.mock import patch

from backend.services.session_cleanup import cleanup_expired_sessions
import asyncio

import pytest

from backend.services.session_cleanup import session_cleanup_worker



def test_cleanup_worker_stops_when_cancelled():
    """Verify that the background worker supports graceful cancellation."""

    async def run_worker_test():
        # Start the background worker as an asynchronous task.
        worker_task = asyncio.create_task(session_cleanup_worker())

        # Allow the worker to begin execution.
        await asyncio.sleep(0)

        # Request graceful shutdown.
        worker_task.cancel()

        # Verify that cancellation propagates correctly.
        with pytest.raises(asyncio.CancelledError):
            await worker_task

    # Run the asynchronous test using Python's built-in event loop.
    asyncio.run(run_worker_test())

@patch("backend.services.session_cleanup.end_expired_session")
@patch("backend.services.session_cleanup.get_expired_session_ids")
def test_cleanup_deletes_expired_sessions(
    mock_get_expired_ids,
    mock_end_expired_session,
):
    """Verify that all expired session candidates are processed."""

    # Simulate two expired sessions.
    mock_get_expired_ids.return_value = [10, 20]

    # Simulate successful deletion of both sessions.
    mock_end_expired_session.return_value = True

    deleted_count = cleanup_expired_sessions()

    assert deleted_count == 2

    # Verify that each expired session was processed exactly once.
    assert mock_end_expired_session.call_count == 2
    mock_end_expired_session.assert_any_call(10)
    mock_end_expired_session.assert_any_call(20)


@patch("backend.services.session_cleanup.end_expired_session")
@patch("backend.services.session_cleanup.get_expired_session_ids")
def test_cleanup_preserves_sessions_that_are_no_longer_expired(
    mock_get_expired_ids,
    mock_end_expired_session,
):
    """Verify that sessions refreshed before deletion are preserved."""

    # Session 10 was identified as expired, but its activity was refreshed.
    mock_get_expired_ids.return_value = [10]
    mock_end_expired_session.return_value = False

    deleted_count = cleanup_expired_sessions()

    # No session should be counted as deleted.
    assert deleted_count == 0
    mock_end_expired_session.assert_called_once_with(10)


@patch("backend.services.session_cleanup.end_expired_session")
@patch("backend.services.session_cleanup.get_expired_session_ids")
def test_cleanup_continues_after_individual_session_failure(
    mock_get_expired_ids,
    mock_end_expired_session,
):
    """Verify that one failed deletion does not stop other cleanups."""

    # Simulate three expired sessions.
    mock_get_expired_ids.return_value = [10, 20, 30]

    # The second session fails, but the third should still be processed.
    mock_end_expired_session.side_effect = [
        True,
        RuntimeError("Simulated cleanup failure"),
        True,
    ]

    deleted_count = cleanup_expired_sessions()

    assert deleted_count == 2
    assert mock_end_expired_session.call_count == 3
