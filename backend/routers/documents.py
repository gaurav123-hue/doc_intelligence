
"""API routes for uploading and listing documents."""

import hashlib
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from psycopg.errors import UniqueViolation
from pydantic import BaseModel

from backend.database import (
    create_uploaded_document,
    get_document_by_hash,
    get_documents,
)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Keep uploaded files outside the source-code directories.
STORAGE_DIR = Path("storage/documents")

# Enforce a 10 MiB upload limit and allow only supported extensions.
MAX_FILE_SIZE = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {".pdf", ".txt", ".docx"}


class DocumentResponse(BaseModel):
    """Metadata returned by document API endpoints."""

    id: int
    filename: str
    file_type: str | None
    status: str
    created_at: datetime


@router.get("", response_model=list[DocumentResponse])
def list_documents():
    """Return document records ordered by database ID."""

    try:
        return get_documents()
    except Exception as exc:
        # Avoid exposing database credentials or internal errors to clients.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve documents",
        ) from exc


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(file: UploadFile = File(...)):
    """Validate, store, and register a document while rejecting duplicates."""

    try:
        # Strip any client-supplied directory components from the filename.
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()

        if not filename or extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF, TXT, and DOCX files are allowed",
            )

        # Read only one byte beyond the limit so oversized uploads are detected.
        content = await file.read(MAX_FILE_SIZE + 1)

        if not content:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="The file is empty",
            )

        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_CONTENT_TOO_LARGE,
                detail="The file exceeds the 10 MB limit",
            )

        # Hash the file bytes so identical content is detected despite different names.
        content_hash = hashlib.sha256(content).hexdigest()
        file_type = extension.lstrip(".").upper()

        try:
            # Check existing records before attempting to store a new document.
            existing = get_document_by_hash(content_hash)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to check for duplicate documents",
            ) from exc

        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "This file's content already exists as "
                    f"document ID {existing['id']}"
                ),
            )

        # Use a content-derived path so each distinct file has a stable name.
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        destination = STORAGE_DIR / f"{content_hash}{extension}"

        # Track whether this request created the file. Only that request may
        # remove it during cleanup; never delete a pre-existing file.
        created_file = False

        try:
            # Exclusive creation prevents overwriting a file created by another request.
            with destination.open("xb") as stored_file:
                created_file = True
                stored_file.write(content)

        except FileExistsError as exc:
            # The same content may be in storage already, even if its database
            # record is not yet visible. Preserve the existing file.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A file with identical content already exists or is being uploaded",
            ) from exc

        try:
            # The database's unique content-hash index is the final duplicate safeguard.
            return create_uploaded_document(
                filename=filename,
                file_type=file_type,
                content_hash=content_hash,
            )

        except UniqueViolation as exc:
            # Remove only the file created by this request after a duplicate insert.
            if created_file:
                destination.unlink(missing_ok=True)

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A document with identical content already exists",
            ) from exc

        except Exception:
            # Avoid leaving our newly created file behind if database insertion fails.
            if created_file:
                destination.unlink(missing_ok=True)

            raise

    except HTTPException:
        # Preserve deliberate client errors such as 400, 409, and 413.
        raise
    except Exception as exc:
        # Keep unexpected internal details out of the API response.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded document",
        ) from exc
    finally:
        # Release the uploaded-file resource on success and every failure path.
        await file.close()
