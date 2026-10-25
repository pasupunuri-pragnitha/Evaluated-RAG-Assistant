-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Table: documents
-- Tracks ingested source files, versioning, and document metadata
CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    source_path TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content_hash TEXT,
    version INT NOT NULL DEFAULT 1,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- Table: chunks
-- Stores chunked markdown text, token counts, embeddings, and tsvector for hybrid search
CREATE TABLE IF NOT EXISTS chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    chunk_index INT NOT NULL,
    heading_path TEXT,
    content TEXT NOT NULL,
    token_count INT NOT NULL DEFAULT 0,
    embedding vector(384),
    tsv tsvector GENERATED ALWAYS AS (to_tsvector('english', content)) STORED,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_document_chunk UNIQUE (document_id, chunk_index)
);

-- HNSW Index for fast vector similarity search (Cosine Distance)
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_hnsw 
ON chunks USING hnsw (embedding vector_cosine_ops);

-- GIN Index on tsvector for Full-Text Search (Phase 2 hybrid search)
CREATE INDEX IF NOT EXISTS idx_chunks_tsv 
ON chunks USING gin (tsv);

-- B-Tree Index on foreign key for performant cascading deletes & doc lookups
CREATE INDEX IF NOT EXISTS idx_chunks_document_id 
ON chunks (document_id);
