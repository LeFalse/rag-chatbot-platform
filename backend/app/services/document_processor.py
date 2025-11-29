"""Document processing with various extraction and chunking strategies."""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Protocol


@dataclass
class Chunk:
    """Represents a single chunk of content."""

    content: str
    start_char: int
    end_char: int
    start_line: int | None = None
    end_line: int | None = None
    page: int | None = None
    section: str | None = None


class TextExtractor(ABC):
    """Abstract base class for text extraction from different formats."""

    @abstractmethod
    async def extract(self, file_path: str) -> str:
        """Extract text from file.

        Args:
            file_path: Path to the file.

        Returns:
            Extracted text.

        Raises:
            ValueError: If extraction fails.
        """
        ...


class PlainTextExtractor(TextExtractor):
    """Extract text from plain text files."""

    async def extract(self, file_path: str) -> str:
        """Extract text from a text file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


class MarkdownExtractor(TextExtractor):
    """Extract text from Markdown files."""

    async def extract(self, file_path: str) -> str:
        """Extract text from a Markdown file."""
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()


class ChunkingStrategy(ABC):
    """Abstract base class for chunking strategies."""

    @abstractmethod
    def chunk(self, text: str, **kwargs) -> list[Chunk]:
        """Split text into chunks.

        Args:
            text: Text to chunk.
            **kwargs: Strategy-specific parameters.

        Returns:
            List of chunks with metadata.
        """
        ...


class FixedSizeChunking(ChunkingStrategy):
    """Split text into fixed-size chunks with overlap."""

    def chunk(
        self,
        text: str,
        chunk_size: int = 512,
        overlap: int = 50,
    ) -> list[Chunk]:
        """Split text into fixed-size chunks with overlap.

        Args:
            text: Text to chunk.
            chunk_size: Size of each chunk in characters.
            overlap: Number of overlapping characters between chunks.

        Returns:
            List of chunks.
        """
        chunks: list[Chunk] = []
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))

            # Avoid cutting off mid-word by finding the last space
            if end < len(text) and text[end] != " ":
                last_space = text.rfind(" ", start, end)
                if last_space > start:
                    end = last_space

            content = text[start:end].strip()
            if content:
                chunks.append(
                    Chunk(
                        content=content,
                        start_char=start,
                        end_char=end,
                    )
                )

            # Move start position for next chunk (with overlap)
            start = end - overlap
            if start < 0:
                break

        return chunks


class SentenceChunking(ChunkingStrategy):
    """Split text into sentence-based chunks."""

    def chunk(
        self,
        text: str,
        chunk_size: int = 3,
        overlap: int = 1,
    ) -> list[Chunk]:
        """Split text into sentence-based chunks.

        Args:
            text: Text to chunk.
            chunk_size: Number of sentences per chunk.
            overlap: Number of overlapping sentences between chunks.

        Returns:
            List of chunks.
        """
        # Split by sentence (basic approach using regex)
        sentence_pattern = r"(?<=[.!?])\s+"
        sentences = re.split(sentence_pattern, text)
        sentences = [s.strip() for s in sentences if s.strip()]

        chunks: list[Chunk] = []
        start_idx = 0

        while start_idx < len(sentences):
            end_idx = min(start_idx + chunk_size, len(sentences))
            chunk_sentences = sentences[start_idx:end_idx]
            content = " ".join(chunk_sentences).strip()

            if content:
                # Calculate character positions
                start_char = text.find(chunk_sentences[0])
                end_char = text.find(
                    chunk_sentences[-1], start_char
                ) + len(chunk_sentences[-1])

                chunks.append(
                    Chunk(
                        content=content,
                        start_char=start_char if start_char >= 0 else 0,
                        end_char=end_char if end_char >= 0 else len(content),
                    )
                )

            start_idx = end_idx - overlap
            if start_idx < 0:
                break

        return chunks


class ParagraphChunking(ChunkingStrategy):
    """Split text into paragraph-based chunks with size limit."""

    def chunk(
        self,
        text: str,
        max_chunk_size: int = 512,
        paragraphs_per_chunk: int = 2,
    ) -> list[Chunk]:
        """Split text into paragraph-based chunks.

        Args:
            text: Text to chunk.
            max_chunk_size: Maximum characters per chunk.
            paragraphs_per_chunk: Max paragraphs per chunk.

        Returns:
            List of chunks.
        """
        # Split by double newline (paragraph boundary)
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        chunks: list[Chunk] = []
        current_chunk: list[str] = []
        current_size = 0
        chunk_start_char = 0

        for para in paragraphs:
            para_size = len(para)

            # If adding this paragraph would exceed limits, create a chunk
            if (
                current_chunk
                and (
                    len(current_chunk) >= paragraphs_per_chunk
                    or current_size + para_size > max_chunk_size
                )
            ):
                content = "\n\n".join(current_chunk).strip()
                chunk_end_char = chunk_start_char + len(content)

                chunks.append(
                    Chunk(
                        content=content,
                        start_char=chunk_start_char,
                        end_char=chunk_end_char,
                    )
                )

                current_chunk = []
                current_size = 0
                chunk_start_char = chunk_end_char

            current_chunk.append(para)
            current_size += para_size + 2  # +2 for newlines

        # Add remaining chunk
        if current_chunk:
            content = "\n\n".join(current_chunk).strip()
            chunk_end_char = chunk_start_char + len(content)

            chunks.append(
                Chunk(
                    content=content,
                    start_char=chunk_start_char,
                    end_char=chunk_end_char,
                )
            )

        return chunks


class DocumentProcessor:
    """Main processor for documents - coordinates extraction and chunking."""

    def __init__(
        self,
        extractor: TextExtractor,
        chunking_strategy: ChunkingStrategy,
    ):
        """Initialize processor with extraction and chunking strategies.

        Args:
            extractor: Strategy for extracting text from files.
            chunking_strategy: Strategy for splitting text into chunks.
        """
        self.extractor = extractor
        self.chunking_strategy = chunking_strategy

    async def process(
        self,
        file_path: str,
        **chunking_kwargs,
    ) -> list[Chunk]:
        """Process a document from file path.

        Args:
            file_path: Path to the document.
            **chunking_kwargs: Parameters for chunking strategy.

        Returns:
            List of chunks with metadata.

        Raises:
            ValueError: If extraction or chunking fails.
        """
        text = await self.extractor.extract(file_path)
        return self.chunking_strategy.chunk(text, **chunking_kwargs)
