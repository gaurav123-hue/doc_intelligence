
"""Coordinate text extraction and persistence for uploaded documents."""

from pathlib import Path

# Import database operations used to save extracted text and update status.
from backend.database import save_extracted_text, update_document_status

# Import the service that extracts text from supported file formats.
from backend.services.text_extraction import extract_text


def process_document(document_id: int, file_path: str | Path) -> None:
    """Extract and save text, then update the document's processing status."""

    try:
        # Extract text before writing anything to the content table.
        extracted_text = extract_text(file_path)

        # Persist content before marking the document as successfully processed.
        save_extracted_text(document_id, extracted_text)

        # Mark the document processed only after its text has been saved.
        update_document_status(document_id, "processed")

    except Exception:
        # Attempt to record failure without hiding the original exception.
        try:
            update_document_status(document_id, "failed")
        except Exception:
            # Preserve the original processing error if status recording also fails.
            pass

        # Let the caller decide how to report the processing failure.
        raise
