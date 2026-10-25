# Evaluated RAG Assistant Architecture

An end-to-end overview of the Evaluated RAG Assistant system design and component interactions.

## System Overview

The Evaluated RAG Assistant is an intelligent question-answering system designed to index technical documentation and provide cited, grounded answers. It leverages PostgreSQL with the pgvector extension for scalable vector search, combined with modern dense retrieval models.

The system ensures that answers are derived exclusively from the ingested knowledge corpus, strictly preventing hallucinations and unsupported extrapolation.

## Data Ingestion Pipeline

The ingestion pipeline processes Markdown files from local storage.

### Markdown Parsing and Heading Hierarchy

Documents are ingested recursively from the documentation directory. Markdown headings from level 1 to level 6 are parsed into a hierarchical heading path. For instance, a subsection inside a guide will be tagged with a breadcrumb like "Guide > Setup > Installation".

### Token-Bounded Chunking

Chunks are generated with a target size of approximately 400 tokens and an overlap of 50 tokens. Every chunk is tokenized using the embedding model's native tokenizer to guarantee that no chunk ever breaches the model's 512-token context window.

### Batch Embeddings

Chunks are embedded in batches using the `BAAI/bge-small-en-v1.5` sentence-transformer model. Document embeddings are L2 normalized and generated without search query prefixes.

## Database Storage and Indexing

PostgreSQL 16 serves as the primary data store and vector engine.

### Documents and Chunks Tables

Source documents are stored in the `documents` table with their unique source path, title, and SHA-256 content hash. Chunks are stored in the `chunks` table with a foreign key referencing their parent document.

### HNSW Vector Indexing

An HNSW index using cosine distance operators (`vector_cosine_ops`) is built on the chunk embeddings to provide sub-millisecond approximate nearest neighbor lookups.
