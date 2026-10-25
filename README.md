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
