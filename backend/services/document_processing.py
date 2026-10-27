
"""Coordinate extraction, chunking, and persistence for uploaded documents."""

from pathlib import Path

# Import the database operations used by the processing pipeline.
from backend.database import (
    save_document_chunks,
    save_extracted_text,
    update_document_status,
)

# Import the text-processing functions used by the pipeline.
from backend.services.text_chunking import chunk_text
from backend.services.text_extraction import extract_text


def process_document(document_id: int, file_path: str | Path) -> None:
    """Extract document text, save chunks, and record processing status."""
    try:
        # Step 1: Extract readable text from the uploaded file.
        extracted_text = extract_text(file_path)

        # Step 2: Save the complete text before creating smaller chunks.
        save_extracted_text(document_id, extracted_text)

        # Step 3: Split the text into overlapping chunks for later retrieval.
        chunks = chunk_text(extracted_text)

        # Guard against an unexpected empty result from the chunking step.
        if not chunks:
            raise ValueError("Document text produced no chunks")

        # Step 4: Persist all chunks before reporting successful processing.
        save_document_chunks(document_id, chunks)

        # Step 5: Mark the document processed only after every step succeeds.
        update_document_status(document_id, "processed")

    except Exception:
        # Record the failure so the API does not report a successful document.
        try:
            update_document_status(document_id, "failed")
        except Exception:
            # Preserve the original error if recording failure also fails.
            pass

        # Let the caller handle or log the original processing error.
        raise
