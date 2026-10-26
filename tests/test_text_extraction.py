
"""Tests for extracting text from supported document formats."""

from docx import Document
from pypdf import PdfWriter
import pytest

from backend.services.text_extraction import (
    TextExtractionError,
    extract_text,
)


def test_extract_text_from_txt(tmp_path):
    """TXT extraction should return the file's text without outer whitespace."""
    file_path = tmp_path / "notes.txt"
    file_path.write_text("  Hello document intelligence!  ", encoding="utf-8")

    assert extract_text(file_path) == "Hello document intelligence!"


def test_extract_text_from_docx(tmp_path):
    """DOCX extraction should return paragraph text in order."""
    file_path = tmp_path / "notes.docx"

    # Create a real DOCX file so the test exercises the actual parser.
    document = Document()
    document.add_paragraph("First paragraph")
    document.add_paragraph("Second paragraph")
    document.save(file_path)

    assert extract_text(file_path) == "First paragraph\nSecond paragraph"


def test_extract_text_rejects_unsupported_format(tmp_path):
    """Unsupported extensions should produce a clear extraction error."""
    file_path = tmp_path / "notes.csv"
    file_path.write_text("a,b,c", encoding="utf-8")

    with pytest.raises(TextExtractionError, match="Unsupported document format"):
        extract_text(file_path)


def test_extract_text_rejects_empty_txt(tmp_path):
    """A file with no usable text should be rejected."""
    file_path = tmp_path / "empty.txt"
    file_path.write_text("   \n  ", encoding="utf-8")

    with pytest.raises(TextExtractionError, match="No extractable text"):
        extract_text(file_path)


def test_extract_text_rejects_invalid_pdf(tmp_path):
    """Malformed PDFs should be reported as extraction errors."""
    file_path = tmp_path / "broken.pdf"
    file_path.write_bytes(b"This is not a valid PDF")

    with pytest.raises(TextExtractionError, match="Could not extract text"):
        extract_text(file_path)


def test_extract_text_rejects_pdf_without_text(tmp_path):
    """A valid but empty PDF should fail because it has no extractable text."""
    file_path = tmp_path / "empty.pdf"

    # A PDF with a blank page is valid but contains no readable text.
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=300)

    with file_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    with pytest.raises(TextExtractionError, match="No extractable text"):
        extract_text(file_path)



def test_extract_text_from_docx_includes_tables(tmp_path):
    """DOCX extraction should include text stored inside tables."""
    file_path = tmp_path / "report.docx"

    # Build a small real document with both paragraph and table content.
    document = Document()
    document.add_paragraph("Quarterly results")

    table = document.add_table(rows=1, cols=2)
    table.cell(0, 0).text = "Revenue"
    table.cell(0, 1).text = "$5000"
    document.save(file_path)

    extracted = extract_text(file_path)

    assert "Quarterly results" in extracted
    assert "Revenue | $5000" in extracted


def test_extract_text_rejects_missing_file(tmp_path):
    """A missing file should raise the module's documented exception."""
    file_path = tmp_path / "missing.txt"

    with pytest.raises(TextExtractionError, match="Could not extract text"):
        extract_text(file_path)
