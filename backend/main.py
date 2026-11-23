
"""Main FastAPI application entry point."""

import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.routers.questions import router as questions_router
from backend.routers.documents import router as documents_router
from backend.routers.sessions import router as sessions_router
from backend.services.session_cleanup import session_cleanup_worker


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage background services during application startup and shutdown."""

    # Start the session cleanup worker when FastAPI starts.
    cleanup_task = asyncio.create_task(session_cleanup_worker())

    try:
        yield

    finally:
        # Stop the background worker gracefully during application shutdown.
        cleanup_task.cancel()

        try:
            await cleanup_task
        except asyncio.CancelledError:
            pass


# Register the application lifespan to manage background services.
app = FastAPI(
    title="AI Document Intelligence API",
    lifespan=lifespan,
)

# Register application API routers.
app.include_router(questions_router, prefix="/questions")
app.include_router(documents_router)
app.include_router(sessions_router)


@app.get("/")
def read_root():
    """Return a basic API availability message."""

    return {"message": "AI Document Intelligence API is running"}


@app.get("/health")
def health_check():
    """Return the application health status."""

    return {"status": "healthy"}
