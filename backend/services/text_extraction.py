
"""Extract readable text from supported document formats."""

from pathlib import Path

from docx import Document
from pypdf import PdfReader


# Keep the supported formats consistent with the document upload API.
SUPPORTED_EXTENSIONS = {".txt", ".pdf", ".docx"}


class TextExtractionError(ValueError):
    """Raised when a document cannot be converted into usable text."""


def extract_text(file_path: str | Path) -> str:
    """Extract and return text from a TXT, PDF, or DOCX file.

    Args:
        file_path: Path to an already-stored document.

    Returns:
        Extracted text with surrounding whitespace removed.

    Raises:
        TextExtractionError: If the format is unsupported, the file cannot
            be read, or the document contains no usable text.
    """
    path = Path(file_path)
    extension = path.suffix.lower()

    # Reject unsupported formats before trying to open the file.
    if extension not in SUPPORTED_EXTENSIONS:
        raise TextExtractionError(
            f"Unsupported document format: {extension or '(no extension)'}"
        )

    try:
        if extension == ".txt":
            # Try UTF-8 first; replace invalid bytes so extraction can continue.
            text = path.read_text(encoding="utf-8", errors="replace")

        elif extension == ".pdf":
            # Extract selectable text from each PDF page in document order.
            reader = PdfReader(str(path))
            page_texts = [
                page.extract_text() or ""
                for page in reader.pages
            ]
            text = "\n".join(page_texts)

        else:
            # Extract paragraphs and tables from the DOCX document body.
            document = Document(str(path))
            content_parts = []

            # Keep non-empty paragraphs in their original paragraph order.
            for paragraph in document.paragraphs:
                if paragraph.text.strip():
                    content_parts.append(paragraph.text)

            # Include table cells so important structured content is not lost.
            for table in document.tables:
                for row in table.rows:
                    cell_texts = [
                        cell.text.strip()
                        for cell in row.cells
                        if cell.text.strip()
                    ]
                    if cell_texts:
                        content_parts.append(" | ".join(cell_texts))

            text = "\n".join(content_parts)

    except Exception as exc:
        # Give callers one predictable exception instead of leaking
        # format-specific parser errors into the API layer.
        raise TextExtractionError(
            f"Could not extract text from {path.name}"
        ) from exc

    # Reject scanned PDFs and other documents with no extractable body text.
    text = text.strip()
    if not text:
        raise TextExtractionError(
            f"No extractable text found in {path.name}"
        )

    return text
