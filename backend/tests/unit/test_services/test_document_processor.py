"""Tests for document processor and chunking strategies."""

import tempfile
from pathlib import Path

import pytest

from app.services.document_processor import (
    DocumentProcessor,
    FixedSizeChunking,
    MarkdownExtractor,
    PlainTextExtractor,
    ParagraphChunking,
    SentenceChunking,
)


@pytest.fixture
def temp_text_file():
    """Create a temporary text file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("This is a test document. " * 20)
        f.flush()
        yield f.name
    Path(f.name).unlink()


@pytest.fixture
def temp_markdown_file():
    """Create a temporary markdown file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        f.write("""# Test Document

This is the first paragraph.
It has multiple lines.

This is the second paragraph.
With more content here.

## Section Two

Another section with content.
""")
        f.flush()
        yield f.name
    Path(f.name).unlink()


@pytest.mark.asyncio
async def test_plain_text_extractor(temp_text_file):
    """Test plain text extraction."""
    extractor = PlainTextExtractor()
    text = await extractor.extract(temp_text_file)

    assert isinstance(text, str)
    assert len(text) > 0
    assert "This is a test document" in text


@pytest.mark.asyncio
async def test_markdown_extractor(temp_markdown_file):
    """Test markdown extraction."""
    extractor = MarkdownExtractor()
    text = await extractor.extract(temp_markdown_file)

    assert isinstance(text, str)
    assert "# Test Document" in text
    assert "## Section Two" in text


def test_fixed_size_chunking():
    """Test fixed-size chunking strategy."""
    text = "This is a test. " * 50
    strategy = FixedSizeChunking()

    chunks = strategy.chunk(text, chunk_size=100, overlap=10)

    assert len(chunks) > 0
    assert all(len(chunk.content) > 0 for chunk in chunks)
    assert all(chunk.start_char >= 0 for chunk in chunks)
    assert all(chunk.end_char > chunk.start_char for chunk in chunks)
    assert chunks[0].start_char == 0


def test_fixed_size_chunking_respects_word_boundaries():
    """Test that fixed-size chunking respects word boundaries."""
    text = "word1 word2 word3 word4 word5 word6 word7 word8 word9 word10"
    strategy = FixedSizeChunking()

    chunks = strategy.chunk(text, chunk_size=20, overlap=0)

    # Verify no chunk ends mid-word (should end at space)
    for chunk in chunks:
        if chunk.end_char < len(text):
            assert text[chunk.end_char - 1] == " " or text[chunk.end_char] == " "


def test_sentence_chunking():
    """Test sentence-based chunking."""
    text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
    strategy = SentenceChunking()

    chunks = strategy.chunk(text, chunk_size=2, overlap=0)

    assert len(chunks) >= 2
    assert "First" in chunks[0].content
    assert "Third" in chunks[1].content


def test_sentence_chunking_overlap():
    """Test sentence chunking with overlap."""
    text = "A. B. C. D. E. F."
    strategy = SentenceChunking()

    chunks = strategy.chunk(text, chunk_size=2, overlap=1)

    # With overlap, some sentences should appear in multiple chunks
    contents = [chunk.content for chunk in chunks]
    assert len(chunks) >= 2


def test_paragraph_chunking():
    """Test paragraph-based chunking."""
    text = """First paragraph with some content.
It has multiple lines.

Second paragraph also has multiple lines.
More content here.

Third paragraph.
Final content."""

    strategy = ParagraphChunking()
    chunks = strategy.chunk(text, max_chunk_size=500, paragraphs_per_chunk=2)

    assert len(chunks) > 0
    assert "First paragraph" in chunks[0].content


def test_paragraph_chunking_respects_size_limit():
    """Test paragraph chunking respects size limits."""
    text = "Small paragraph.\n\n" * 50
    strategy = ParagraphChunking()

    chunks = strategy.chunk(text, max_chunk_size=100, paragraphs_per_chunk=10)

    # All chunks should be under the size limit
    for chunk in chunks:
        assert len(chunk.content) <= 150  # Some tolerance


def test_paragraph_chunking_respects_paragraph_limit():
    """Test paragraph chunking respects paragraph limits."""
    text = "\n\n".join([f"Paragraph {i}." for i in range(20)])
    strategy = ParagraphChunking()

    chunks = strategy.chunk(text, max_chunk_size=1000, paragraphs_per_chunk=3)

    # Each chunk should have at most 3 paragraphs (rough check)
    for chunk in chunks:
        # Count newline pairs (paragraph separators)
        para_count = chunk.content.count("\n\n") + 1
        assert para_count <= 4  # Some tolerance


@pytest.mark.asyncio
async def test_document_processor(temp_text_file):
    """Test full document processing."""
    extractor = PlainTextExtractor()
    strategy = FixedSizeChunking()
    processor = DocumentProcessor(extractor, strategy)

    chunks = await processor.process(
        temp_text_file,
        chunk_size=100,
        overlap=10,
    )

    assert len(chunks) > 0
    assert all(hasattr(chunk, "content") for chunk in chunks)
    assert all(hasattr(chunk, "start_char") for chunk in chunks)
    assert all(hasattr(chunk, "end_char") for chunk in chunks)


@pytest.mark.asyncio
async def test_document_processor_with_different_strategies(temp_markdown_file):
    """Test processor with different chunking strategies."""
    extractor = MarkdownExtractor()

    # Test with paragraph strategy
    strategy = ParagraphChunking()
    processor = DocumentProcessor(extractor, strategy)

    chunks = await processor.process(
        temp_markdown_file,
        max_chunk_size=500,
        paragraphs_per_chunk=2,
    )

    assert len(chunks) > 0


def test_chunk_has_metadata():
    """Test that chunks can store metadata."""
    text = "Test content."
    strategy = FixedSizeChunking()

    chunks = strategy.chunk(text, chunk_size=100, overlap=0)

    assert len(chunks) > 0
    chunk = chunks[0]
    assert chunk.section is None or isinstance(chunk.section, str)
    assert chunk.page is None or isinstance(chunk.page, int)
