# Evaluated RAG Assistant

A production-grade Retrieval-Augmented Generation (RAG) assistant built on PostgreSQL + pgvector, FastAPI, sentence-transformers (`BAAI/bge-small-en-v1.5`), and Gemini.

## Tech Stack

- **Runtime**: Python 3.11
- **API**: FastAPI & Uvicorn
- **Vector Database**: PostgreSQL 16 + pgvector (HNSW indexing with cosine distance)
- **Database Driver**: `psycopg` (v3) + `pgvector`
- **Embeddings**: `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **LLM**: Gemini API
- **Containerization**: Docker Compose
- **Testing**: pytest

## Project Structure

```text
Evaluated-RAG-Assistant/
├── app/              # FastAPI application endpoints and schemas
├── ingest/           # Markdown document ingestion, heading chunking, and batch embedding
├── retrieval/        # Vector similarity search over pgvector
├── eval/             # Evaluation pipelines (Phase 2+)
├── ui/               # User interface (Phase 2+)
├── tests/            # Test suite (chunker, search, API)
├── db/               # Database initialization SQL scripts
├── scripts/          # Helper scripts (docs downloader)
├── data/
│   └── docs/         # Source Markdown knowledge documents
├── docker-compose.yml# Container orchestration for pgvector service
├── .env.example      # Environment variables template
├── requirements.txt  # Python dependencies
└── README.md
```

## Quick Start

1. Copy `.env.example` to `.env` and fill in credentials:

   ```bash
   cp .env.example .env
   ```

2. Start the PostgreSQL + pgvector container:

   ```bash
   docker compose up -d
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Download FastAPI documentation (shallow clone):

   ```bash
   python scripts/download_docs.py
   ```

5. Ingest documentation into PostgreSQL:

   ```bash
   python -m ingest.run --docs data/docs
   ```

## Configuration

The assistant is configured via environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `RETRIEVER` | `hybrid-bm25` | Retriever pipeline: `vector`, `hybrid-bm25`, or `hybrid-bm25-rerank`. |
| `USE_RERANKER` | `false` | Whether to enable cross-encoder reranking (`BAAI/bge-reranker-base`) over the top 20 candidates. |
| `MIN_SCORE` | `0.60` | Score gate threshold applied to `top_vector_score` across all retrievers. Queries with `top_vector_score < MIN_SCORE` are refused without invoking the LLM. |
| `RERANK_MIN_SCORE` | *unset* | Optional score gate threshold applied to `top_rerank_score` when `USE_RERANKER` is true. `RERANK_MIN_SCORE` is not set by default because the v1-derived 0.502 threshold passes 5 of 11 unanswerable questions on v2. |
| `APP_PORT` | `8001` | Server listening port. |

