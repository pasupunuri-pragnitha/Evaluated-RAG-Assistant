# Evaluated RAG Assistant

A retrieval-augmented question-answering assistant over the FastAPI
documentation, built on PostgreSQL + pgvector. It answers with citations and
refuses when the evidence is weak. The project's focus is measurement: every
retrieval change was compared against a frozen baseline on a development set and
a held-out set, with decision rules written down before the runs.

## Results at a glance

(Retrieval only, pages judged by whether a retrieved chunk comes from an
expected page. 31 answerable questions in v1, 20 in v2. One v2 question is 5
percentage points.)

| Retriever | v1 Hit@1 | v1 Hit@5 | v1 MRR | v2 Hit@1 | v2 Hit@5 | v2 MRR |
|---|---|---|---|---|---|---|
| Vector only (baseline) | 21 | 29 | 0.768 | 10 | 17 | 0.645 |
| BM25 only | 18 | 27 | 0.715 | 10 | 16 | 0.618 |
| Hybrid (vector + BM25, RRF) | 22 | 29 | 0.809 | 13 | 18 | 0.739 |
| Hybrid + cross-encoder reranker | 24 | 29 | 0.844 | 15 | 18 | 0.808 |

Hit counts are out of 31 (v1) and 20 (v2). Full tables, the Postgres full-text
variant, and all provenance notes are in RESULTS.md.

## What worked, what didn't

- Hybrid search (vector + BM25 with rank fusion) beat vector-only on both
  sets; the gain is small (a few questions).
- Postgres full-text ranking, used as the keyword half, made results worse than
  vector-only; BM25 fixed it.
- The reranker passed its pre-registered rule on the held-out set, but on the
  15 revised questions it was flat (MRR 0.817 vs 0.811); post-hoc, the gain comes from
  two questions. It also adds about 7.5 s per query on CPU, so it is off by
  default.
- A similarity-score gate cannot reliably separate near-miss questions from
  answerable ones (lowest answerable score 0.669 vs highest unanswerable 0.759
  on v1).
- End to end, the local Llama 3.1 8B model refused 3 questions whose answer was in the
  retrieved text (2 on v1, 1 on v2), and in manual review of 15 sampled answers per set
  about half were fully correct (v1: 7 of 15, v2: 7 of 15). See RESULTS.md,
  "Answer quality", and FAILURES.md.

## How it works

```text
Indexing:
  docs (Markdown) -> loader (inline code examples, strip HTML)
                  -> heading-aware chunker (~400 tokens, ~50 overlap)
                  -> bge-small embeddings
                  -> PostgreSQL + pgvector (HNSW) & BM25 index (in memory)

Querying:
  question -> vector search + BM25 search
           -> reciprocal rank fusion (pool 50, k=60) -> top 5 chunks
           -> [optional cross-encoder reranker over top 20]
           -> cosine gate (refuse if top_vector_score < 0.60, no LLM call)
           -> local Llama 3.1 8B ("answer only from the context, cite as [n]")
           -> answer + citations + warnings
```

**Ingestion**: Document ingestion is idempotent, computing a SHA-256 hash of each Markdown file and skipping unchanged files. Modified or new documents are chunked along heading hierarchies (~400 target tokens, ~50 token overlap, merging blocks under 80 tokens) and versioned in PostgreSQL. Chunks are embedded with `BAAI/bge-small-en-v1.5` and indexed with pgvector HNSW, while an in-memory BM25Okapi index is loaded at server startup.

**Retrieval**: Questions are queried across vector search (cosine distance) and an in-memory BM25 index. Candidate chunks from both retrievers (top 50 each) are combined using Reciprocal Rank Fusion (RRF with k=60) to select the top 5 chunks. If cross-encoder reranking is enabled, the top 20 RRF candidates are re-scored with `BAAI/bge-reranker-base` before returning the top 5.

**Refusal gate**: Before invoking the LLM, the pipeline checks the top chunk's cosine similarity score against a threshold (`MIN_SCORE = 0.60`). If `top_vector_score < 0.60`, the request short-circuits immediately without calling the LLM, returning `"I don't know based on the documentation."`. When reranking is active and `RERANK_MIN_SCORE` is set, a secondary gate checks the top rerank score.

**Answer post-processing**: The generated answer is checked for model refusal, and citation brackets (`[n]`) are parsed and validated against retrieved chunk indices (1 to k). Out-of-bounds citations are removed with a warning, and cited sources are filtered to only those referenced in the text. If the answer contains a fenced code block where more than half of the lines cannot be found in the cited chunk text, a `"code block not found in cited sources"` warning is attached.

### Response fields (`/ask`)

- `answer`: Generated answer text, cleaned of invalid citation brackets, or the standardized refusal message.
- `refused`: Boolean indicating whether the question was refused by the score gate or the model.
- `sources_cited`: List of retrieved source objects referenced by `[n]` citations in the answer.
- `sources_retrieved`: Complete list of top retrieved source items, each with `source_path`, `title`, `heading_path`, `score` (plain vector retriever only), and retriever scores (`vector_score`, `rrf_score`, and optional `rerank_score`).
- `top_vector_score`: Best cosine similarity from the vector search for the query (this is the value the refusal gate uses; it can exceed the vector score of every chunk in the fused top 5).
- `warnings`: List of validation warnings (e.g. invalid citation removed, no citations, or unverified code block).
- `latency_ms`: Latency breakdown object with `retrieval`, `llm`, `total`, and optional `rerank` in milliseconds.
- `retriever`: The retriever pipeline that handled the request (e.g. `hybrid-bm25` or `hybrid-bm25-rerank`).

## Tech Stack

- **Runtime**: Python 3.11
- **API**: FastAPI & Uvicorn
- **Vector Database**: PostgreSQL 16 + pgvector (HNSW indexing with cosine distance)
- **Database Driver**: `psycopg` (v3) + `pgvector`
- **Embeddings**: `sentence-transformers` (`BAAI/bge-small-en-v1.5`, 384 dimensions)
- **LLM**: local Llama 3.1 8B via Ollama (OpenAI-compatible endpoint)
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

6. Set up Ollama and the custom model:

   Install Ollama, make sure Ollama is running (`ollama serve`), pull the base model, and create `llama31-rag` from the repository's Modelfile:

   ```bash
   ollama pull llama3.1:8b
   ollama create llama31-rag -f Modelfile
   ```

   *Note*: The model needs about 5 GB; on a GPU with 4 GB VRAM it partly runs on CPU, so answers take roughly 6 to 60 seconds.

7. Start the API server:

   ```bash
   python -m app.main
   ```

### First run note

The embedding model (`BAAI/bge-small-en-v1.5`) downloads automatically on first use. The optional cross-encoder reranker (`BAAI/bge-reranker-base`, about 1.1 GB) downloads only if `USE_RERANKER=true`.

Embeddings run on whichever device SentenceTransformer selects (CUDA if available, otherwise CPU); the evaluation results in RESULTS.md were produced on a laptop with a 4 GB GPU. Scores can differ slightly on other hardware.

The BM25 index is built in the background at startup; /health answers immediately and the first /ask waits for the index if it is not ready.

## Configuration

The assistant is configured via environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `RETRIEVER` | `hybrid-bm25` | Retriever pipeline: `vector`, `hybrid-bm25`, or `hybrid-bm25-rerank`. |
| `USE_RERANKER` | `false` | Whether to enable cross-encoder reranking (`BAAI/bge-reranker-base`) over the top 20 candidates. |
| `MIN_SCORE` | `0.60` | Score gate threshold applied to `top_vector_score` across all retrievers. Queries with `top_vector_score < MIN_SCORE` are refused without invoking the LLM. |
| `RERANK_MIN_SCORE` | *unset* | Optional score gate threshold applied to `top_rerank_score` when `USE_RERANKER` is true. `RERANK_MIN_SCORE` is not set by default because the v1-derived 0.502 threshold passes 5 of 11 unanswerable questions on v2. |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Base URL for Ollama / OpenAI-compatible LLM endpoint. |
| `LLM_MODEL` | `llama31-rag` | Model name to invoke for answer generation. |
| `LLM_TIMEOUT_SECONDS` | `300` | Request timeout in seconds for LLM generation calls. |
| `APP_PORT` | `8001` | Server listening port. |

