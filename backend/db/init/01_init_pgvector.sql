-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Verify installation
SELECT extversion FROM pg_extension WHERE extname = 'vector';
