
"""API routes for uploading and listing documents."""

import hashlib
import logging
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
from backend.services.document_processing import process_document

# Keep detailed processing errors in server logs, not API responses.
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/documents", tags=["Documents"])

# Store uploaded files outside the source-code directories.
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
    """Validate, store, register, and process an uploaded document."""

    try:
        # Strip any client-supplied directory components from the filename.
        filename = Path(file.filename or "").name
        extension = Path(filename).suffix.lower()

        if not filename or extension not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF, TXT, and DOCX files are allowed",
            )

        # Read only one byte beyond the limit to detect oversized uploads.
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

        # Hash the bytes so identical content is detected despite different names.
        content_hash = hashlib.sha256(content).hexdigest()
        file_type = extension.lstrip(".").upper()

        try:
            # Check for an existing document before storing a new file.
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

        # Give each distinct file a stable, content-derived storage path.
        STORAGE_DIR.mkdir(parents=True, exist_ok=True)
        destination = STORAGE_DIR / f"{content_hash}{extension}"

        # Only remove the file if this request successfully created it.
        created_file = False

        try:
            # Exclusive creation prevents overwriting an existing file.
            with destination.open("xb") as stored_file:
                created_file = True
                stored_file.write(content)

        except FileExistsError as exc:
            # Preserve a file that may belong to another concurrent upload.
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "A file with identical content already exists "
                    "or is being uploaded"
                ),
            ) from exc

        try:
            # Create metadata before processing so failures can be tracked.
            document = create_uploaded_document(
                filename=filename,
                file_type=file_type,
                content_hash=content_hash,
            )

        except UniqueViolation as exc:
            # The database unique index protects against concurrent duplicates.
            if created_file:
                try:
                    destination.unlink(missing_ok=True)
                except OSError:
                    # Log cleanup failures without masking the database error.
                    logger.exception(
                        "Could not remove uploaded file after duplicate insertion: %s",
                        destination,
                    )

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A document with identical content already exists",
            ) from exc

        except Exception as exc:
            # Avoid leaving an orphaned file if metadata insertion fails.
            if created_file:
                try:
                    destination.unlink(missing_ok=True)
                except OSError:
                    # Preserve the original error and log the cleanup problem.
                    logger.exception(
                        "Could not remove uploaded file after metadata insertion failed: %s",
                        destination,
                    )

            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to save uploaded document",
            ) from exc

        try:
            # Extract text, persist it, and mark the document as processed.
            process_document(document["id"], destination)

            # Reflect successful processing in the response.
            document["status"] = "processed"

        except Exception:
            # Preserve the file and metadata so the failed document can be retried.
            logger.exception(
                "Processing failed for document ID %s",
                document["id"],
            )

            # The processing service attempts to record failure status in the database.
            document["status"] = "failed"

        # The upload succeeded even if subsequent text processing failed.
        return document

    except HTTPException:
        # Preserve intentional client errors such as 400, 409, and 413.
        raise

    except Exception as exc:
        # Keep unexpected internal details out of the API response.
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to save uploaded document",
        ) from exc

    finally:
        # Release the uploaded-file resource on every success or failure path.
        await file.close()
