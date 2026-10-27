
"""Database operations for document metadata."""

import os
from contextlib import closing

import psycopg
from dotenv import load_dotenv

# Load local environment variables, including DATABASE_URL, from .env.
load_dotenv()


def _get_database_url() -> str:
    """Return the configured database URL or raise a clear error."""
    database_url = os.getenv("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not configured")

    return database_url


def check_database_connection() -> int:
    """Check database connectivity and return the result of SELECT 1."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

    # SELECT 1 should always return one row containing the integer 1.
    return result[0]


def create_document(filename: str, file_type: str) -> dict:
    """Insert document metadata and return the created record."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO documents (filename, file_type)
                    VALUES (%s, %s)
                    RETURNING id, filename, file_type, status, created_at
                    """,
                    (filename, file_type),
                )
                row = cursor.fetchone()

    return {
        "id": row[0],
        "filename": row[1],
        "file_type": row[2],
        "status": row[3],
        "created_at": row[4],
    }


def get_documents() -> list[dict]:
    """Return all document records ordered by ID."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, file_type, status, created_at
                    FROM documents
                    ORDER BY id
                    """
                )
                rows = cursor.fetchall()

    # Convert database tuples into dictionaries for the API layer.
    return [
        {
            "id": row[0],
            "filename": row[1],
            "file_type": row[2],
            "status": row[3],
            "created_at": row[4],
        }
        for row in rows
    ]


def get_document_by_hash(content_hash: str) -> dict | None:
    """Find a document by its SHA-256 content hash."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, filename, file_type, status, created_at
                    FROM documents
                    WHERE content_hash = %s
                    """,
                    (content_hash,),
                )
                row = cursor.fetchone()

    # A missing row means no matching document has been recorded.
    if row is None:
        return None

    return {
        "id": row[0],
        "filename": row[1],
        "file_type": row[2],
        "status": row[3],
        "created_at": row[4],
    }


def create_uploaded_document(
    filename: str,
    file_type: str | None,
    content_hash: str,
) -> dict:
    """Insert metadata for an uploaded document, including its content hash."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO documents (filename, file_type, content_hash)
                    VALUES (%s, %s, %s)
                    RETURNING id, filename, file_type, status, created_at
                    """,
                    (filename, file_type, content_hash),
                )
                row = cursor.fetchone()

    return {
        "id": row[0],
        "filename": row[1],
        "file_type": row[2],
        "status": row[3],
        "created_at": row[4],
    }



def save_extracted_text(document_id: int, extracted_text: str) -> None:
    """Save extracted text for a document, inserting or updating its content."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                # Upsert makes retries safe if this document already has content.
                cursor.execute(
                    """
                    INSERT INTO document_contents (document_id, extracted_text)
                    VALUES (%s, %s)
                    ON CONFLICT (document_id)
                    DO UPDATE SET
                        extracted_text = EXCLUDED.extracted_text,
                        updated_at = CURRENT_TIMESTAMP
                    """,
                    (document_id, extracted_text),
                )


def update_document_status(document_id: int, status: str) -> None:
    """Update processing status for an existing document."""
    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                # Parameterize values to keep SQL safe from injection.
                cursor.execute(
                    """
                    UPDATE documents
                    SET status = %s
                    WHERE id = %s
                    """,
                    (status, document_id),
                )

                # Fail explicitly if the requested document doesn't exist.
                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Document with ID {document_id} does not exist"
                    )


def save_document_chunks(document_id: int, chunks: list[str]) -> None:
    """Replace a document's stored chunks in a single database transaction."""

    # Reject empty input before connecting, so existing chunks are not deleted accidentally.
    if not chunks:
        raise ValueError("at least one chunk is required")

    # Reject blank chunks before making any database changes.
    if any(not chunk.strip() for chunk in chunks):
        raise ValueError("chunks must not be empty or whitespace-only")

    # Open a connection that will be closed even if the operation fails.
    with closing(psycopg.connect(_get_database_url())) as connection:
        # The connection context commits on success and rolls back on error.
        with connection:
            with connection.cursor() as cursor:
                # Remove previous chunks as part of the same transaction.
                cursor.execute(
                    """
                    DELETE FROM document_chunks
                    WHERE document_id = %s
                    """,
                    (document_id,),
                )

                # Assign each chunk a stable, zero-based position.
                chunk_rows = [
                    (document_id, index, chunk.strip())
                    for index, chunk in enumerate(chunks)
                ]

                # Insert the replacement chunks efficiently in one operation.
                cursor.executemany(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_index, chunk_text)
                    VALUES (%s, %s, %s)
                    """,
                    chunk_rows,
                )
