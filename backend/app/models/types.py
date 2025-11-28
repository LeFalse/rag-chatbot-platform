"""Type definitions for domain models."""

from typing import TypedDict


class DocumentMetadata(TypedDict, total=False):
    """Metadata for uploaded documents.

    All fields are optional (total=False) to allow flexibility.
    """

    source: str  # Original source/path
    author: str  # Document author
    title: str  # Document title
    page_count: int  # Number of pages (PDF)
    language: str  # Detected language
    created_date: str  # Original creation date (ISO format)
    mime_type: str  # Full MIME type
    encoding: str  # Text encoding


class ChunkMetadata(TypedDict, total=False):
    """Metadata for document chunks.

    All fields are optional (total=False) to allow flexibility.
    """

    page: int  # Page number (1-indexed)
    section: str  # Section/chapter name
    start_char: int  # Start character position in original document
    end_char: int  # End character position in original document
    start_line: int  # Start line number
    end_line: int  # End line number
    heading: str  # Nearest heading/title
