
"""Database operations for document metadata and session management."""

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


class SessionDocumentLimitExceeded(Exception):
    """Raised when a session has reached its maximum document limit."""


# ---------------------------------------------------------------------------
# Session operations
# ---------------------------------------------------------------------------

def create_session(token_hash: str) -> dict:
    """Create a session using the SHA-256 hash of its secret token."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO sessions (token_hash)
                    VALUES (%s)
                    RETURNING id, created_at, last_activity_at
                    """,
                    (token_hash,),
                )
                row = cursor.fetchone()

    return {
        "id": row[0], # type: ignore
        "created_at": row[1], # type: ignore
        "last_activity_at": row[2], # type: ignore
    }


def get_active_session(token_hash: str) -> dict | None:
    """Validate a session and refresh its activity timestamp.

    Sessions inactive for 60 minutes are rejected and cannot be
    reactivated simply by making another request.
    """

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE sessions
                    SET last_activity_at = CURRENT_TIMESTAMP
                    WHERE token_hash = %s
                      AND last_activity_at >=
                          CURRENT_TIMESTAMP - INTERVAL '60 minutes'
                    RETURNING id, created_at, last_activity_at
                    """,
                    (token_hash,),
                )
                row = cursor.fetchone()

    if row is None:
        return None

    return {
        "id": row[0],
        "created_at": row[1],
        "last_activity_at": row[2],
    }


def get_expired_session_ids() -> list[int]:
    """Return IDs of sessions inactive for more than 60 minutes."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                # Identify sessions that have exceeded the inactivity limit.
                cursor.execute(
                    """
                    SELECT id
                    FROM sessions
                    WHERE last_activity_at <
                        CURRENT_TIMESTAMP - INTERVAL '60 minutes'
                    ORDER BY last_activity_at ASC
                    """
                )

                rows = cursor.fetchall()

    # Return only session IDs for the cleanup service.
    return [row[0] for row in rows]


def delete_session(
    session_id: int,
    only_if_expired: bool = False,
) -> dict | None:
    """Atomically delete a session and return its uploaded document metadata.

    The session row lock prevents concurrent uploads from registering
    new documents while the session is being deleted.
    """

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:

                # Lock the session row to serialize deletion with uploads.
                cursor.execute(
                    """
                    SELECT id
                    FROM sessions
                    WHERE id = %s
                      AND (
                          %s = FALSE
                          OR last_activity_at <
                              CURRENT_TIMESTAMP - INTERVAL '60 minutes'
                      )
                    FOR UPDATE
                    """,
                    (session_id, only_if_expired),
)

                session = cursor.fetchone()

                # Return None when the session does not exist.
                if session is None:
                    return None

                # Capture file metadata before cascading database deletion.
                cursor.execute(
                    """
                    SELECT id, filename, file_type, content_hash
                    FROM documents
                    WHERE session_id = %s
                    ORDER BY id
                    """,
                    (session_id,),
                )

                document_rows = cursor.fetchall()

                # Delete the session and its related database records.
                cursor.execute(
                    """
                    DELETE FROM sessions
                    WHERE id = %s
                    RETURNING id
                    """,
                    (session_id,),
                )

                deleted_session = cursor.fetchone()

    # Return document metadata so the service can remove physical files.
    return {
        "session_id": deleted_session[0], # type: ignore
        "documents": [
            {
                "id": row[0],
                "filename": row[1],
                "file_type": row[2],
                "content_hash": row[3],
            }
            for row in document_rows
        ],
    }



# ---------------------------------------------------------------------------
# General database operations
# ---------------------------------------------------------------------------

def check_database_connection() -> int:
    """Check database connectivity and return the result of SELECT 1."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

    return result[0] # type: ignore


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
        "id": row[0], # type: ignore
        "filename": row[1], # type: ignore
        "file_type": row[2], # type: ignore
        "status": row[3], # type: ignore
        "created_at": row[4], # type: ignore
    }


def get_documents(session_id: int) -> list[dict]:
    """Return documents belonging to one session, ordered by ID."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename, file_type, status, created_at
                FROM documents
                WHERE session_id = %s
                ORDER BY id
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

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


def get_document_by_hash(
    content_hash: str,
    session_id: int,
) -> dict | None:
    """Find a duplicate document within the specified session."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename, file_type, status, created_at
                FROM documents
                WHERE content_hash = %s
                  AND session_id = %s
                """,
                (content_hash, session_id),
            )
            row = cursor.fetchone()

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
    session_id: int,
) -> dict:
    """Insert a document while enforcing the three-file session limit."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:

                # Lock the session row to serialize uploads within this session.
                cursor.execute(
                    """
                    SELECT id
                    FROM sessions
                    WHERE id = %s
                    FOR UPDATE
                    """,
                    (session_id,),
                )
                session = cursor.fetchone()

                if session is None:
                    raise ValueError("Session does not exist.")

                # Count documents while holding the session lock.
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM documents
                    WHERE session_id = %s
                    """,
                    (session_id,),
                )
                document_count = cursor.fetchone()[0] # type: ignore

                # Reject uploads when the session already contains three documents.
                if document_count >= 3:
                    raise SessionDocumentLimitExceeded(
                        "A session can contain a maximum of 3 documents."
                    )

                # Insert the document only after the limit check succeeds.
                cursor.execute(
                    """
                    INSERT INTO documents (
                        filename,
                        file_type,
                        content_hash,
                        session_id
                    )
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, filename, file_type, status, created_at
                    """,
                    (filename, file_type, content_hash, session_id),
                )
                row = cursor.fetchone()

    return {
        "id": row[0], # type: ignore
        "filename": row[1], # type: ignore
        "file_type": row[2], # type: ignore
        "status": row[3], # type: ignore
        "created_at": row[4], # type: ignore
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
                cursor.execute(
                    """
                    UPDATE documents
                    SET status = %s
                    WHERE id = %s
                    """,
                    (status, document_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Document with ID {document_id} does not exist"
                    )


def save_document_chunks(document_id: int, chunks: list[str]) -> None:
    """Replace a document's stored chunks in a single transaction."""

    if not chunks:
        raise ValueError("at least one chunk is required")

    if any(not chunk.strip() for chunk in chunks):
        raise ValueError("chunks must not be empty or whitespace-only")

    with closing(psycopg.connect(_get_database_url())) as connection:
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

                cursor.executemany(
                    """
                    INSERT INTO document_chunks
                        (document_id, chunk_index, chunk_text)
                    VALUES (%s, %s, %s)
                    """,
                    chunk_rows,
                )


# ---------------------------------------------------------------------------
# Embedding operations
# ---------------------------------------------------------------------------

def get_chunks_without_embeddings() -> list[dict]:
    """Return stored chunks that still need an embedding."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT id, chunk_text
                    FROM document_chunks
                    WHERE embedding IS NULL
                    ORDER BY id
                    """
                )
                rows = cursor.fetchall()

    return [
        {"id": row[0], "chunk_text": row[1]}
        for row in rows
    ]


def save_chunk_embedding(chunk_id: int, embedding: list[float]) -> None:
    """Save one generated vector to its corresponding chunk."""

    if len(embedding) != 384:
        raise ValueError("Embedding must contain exactly 384 values")

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE document_chunks
                    SET embedding = %s
                    WHERE id = %s
                    """,
                    (str(embedding), chunk_id),
                )

                if cursor.rowcount == 0:
                    raise ValueError(
                        f"Document chunk with ID {chunk_id} does not exist"
                    )



def search_similar_chunks(
    query_embedding: list[float],
    session_id: int,
    limit: int = 5,
) -> list[dict]:
    """Return the most similar chunks belonging to one session."""

    # Validate the embedding dimensions expected by our vector column.
    if len(query_embedding) != 384:
        raise ValueError("Query embedding must contain exactly 384 values")

    # Prevent invalid or excessively large search requests.
    if not 1 <= limit <= 50:
        raise ValueError("limit must be between 1 and 50")

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                # Filter through the parent document's session ID.
                # This prevents chunks from other sessions appearing in results.
                cursor.execute(
                    """
                    SELECT
                        dc.id,
                        dc.document_id,
                        d.filename,
                        dc.chunk_index,
                        dc.chunk_text,
                        dc.embedding <=> %s::vector AS distance
                    FROM document_chunks dc
                    JOIN documents d ON d.id = dc.document_id
                    WHERE
                        dc.embedding IS NOT NULL
                        AND d.session_id = %s
                    ORDER BY dc.embedding <=> %s::vector
                    LIMIT %s
                    """,
                    (
                        str(query_embedding),
                        session_id,
                        str(query_embedding),
                        limit,
                    ),
                )

                rows = cursor.fetchall()

    # Convert database rows into dictionaries for the RAG pipeline.
    return [
        {
            "chunk_id": row[0],
            "document_id": row[1],
            "filename": row[2],
            "chunk_index": row[3],
            "chunk_text": row[4],
            "distance": float(row[5]),
        }
        for row in rows
    ]


# ---------------------------------------------------------------------------
# Session document cleanup operations
# ---------------------------------------------------------------------------

def get_session_documents(session_id: int) -> list[dict]:
    """Retrieve document metadata belonging to one session.

    The content hash and file type are used to reconstruct physical
    storage paths during session cleanup.
    """

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT id, filename, file_type, content_hash
                FROM documents
                WHERE session_id = %s
                ORDER BY id
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "filename": row[1],
            "file_type": row[2],
            "content_hash": row[3],
        }
        for row in rows
    ]



# ---------------------------------------------------------------------------
# Conversation history operations
# ---------------------------------------------------------------------------

def save_conversation_turn(
    session_id: int,
    question: str,
    answer: str,
    sources: list[dict],
    cited_source_details: list[dict],
    citation_validation: dict,
    result_count: int,
) -> dict:
    """Save a question, generated answer, and citation metadata."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection:
            with connection.cursor() as cursor:
                # Store the complete RAG response against its owning session.
                cursor.execute(
                    """
                    INSERT INTO conversation_turns (
                        session_id,
                        question,
                        answer,
                        sources,
                        cited_source_details,
                        citation_validation,
                        result_count
                    )
                    VALUES (
                        %s, %s, %s, %s, %s, %s, %s
                    )
                    RETURNING id, created_at
                    """,
                    (
                        session_id,
                        question,
                        answer,
                        psycopg.types.json.Jsonb(sources), # type: ignore
                        psycopg.types.json.Jsonb(cited_source_details), # type: ignore
                        psycopg.types.json.Jsonb(citation_validation), # type: ignore
                        result_count,
                    ),
                )

                row = cursor.fetchone()

    return {
        "id": row[0], # type: ignore
        "created_at": row[1], # type: ignore
    }


def get_conversation_history(session_id: int) -> list[dict]:
    """Retrieve conversation turns belonging to one session."""

    with closing(psycopg.connect(_get_database_url())) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT
                    id,
                    question,
                    answer,
                    sources,
                    cited_source_details,
                    citation_validation,
                    result_count,
                    created_at
                FROM conversation_turns
                WHERE session_id = %s
                ORDER BY created_at ASC, id ASC
                """,
                (session_id,),
            )

            rows = cursor.fetchall()

    return [
        {
            "id": row[0],
            "question": row[1],
            "answer": row[2],
            "sources": row[3],
            "cited_source_details": row[4],
            "citation_validation": row[5],
            "result_count": row[6],
            "created_at": row[7],
        }
        for row in rows
    ]
