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

## How the evaluation works

### 1. Question sets

- **v1 (`eval/questions.jsonl`)**: 40 questions (31 answerable, 9 unanswerable). Drafted with AI assistance and source-verified against FastAPI documentation text; used during development to diagnose the full-text retrieval problem and choose BM25 as the keyword retriever (BM25 parameters stayed at the library defaults, k1=1.5 and b=0.75).
- **v2 (`eval/questions_v2.jsonl`)**: 31 questions (20 answerable, 11 unanswerable). Written after analyzing v1 failure modes, kept frozen and untouched until the evaluation decision rules were written down, and reported as the held-out test set.
- **Hit matching**: Evaluated at page level. A retrieval hit occurs if any retrieved top-k chunk originates from an `expected_sources` documentation page.

### 2. Metrics

- **Retrieval**: Hit@1, Hit@3, Hit@5, and Mean Reciprocal Rank (MRR) across answerable questions.
- **Refusal gating**: Refusal rate on unanswerable questions (higher is better) and false-refusal rate on answerable questions with an expected page in top 5 (lower is better).
- **Answer quality**: Manual review of answer samples scored into three categories: `correct`, `partly`, or `incorrect`.

### 3. Pre-registration & Provenance

Decision rules were written into `eval/PREREGISTRATION*.md` before the experimental runs they govern:
- `eval/PREREGISTRATION.md`: Hybrid-BM25 decision rule (committed at `e81b1b2` before the v2 evaluation runs).
- `eval/PREREGISTRATION_RERANK.md` and `PREREGISTRATION_RERANK_ADDENDUM.md`: Cross-encoder reranker decision rule (committed at `f4c6ceb` before the reranker runs).
- `eval/PREREGISTRATION_ANSWERS.md`: End-to-end answer evaluation rules. Written at 19:38 IST (file creation time) before any run, and committed at 19:46 IST after the v1 run had started (19:44 IST), but before the v2 run (19:57 IST) and the recheck run (20:04 IST). The v1 answer results cannot be proven by git history to postdate the committed rules; v2 and recheck can.

### 4. Frozen results

All raw results used in the evaluation tables are preserved in `eval/baselines/`:
- Retrieval runs: `baseline-vector-only.json`, `bm25-only.json`, `fulltext-only.json`, `hybrid-bm25-v1.json`, `hybrid-rrf-v1.json`, `hybrid-rrf-tiebreak.json`, `v1-hybrid-bm25-rerank.json`, `v2-vector-only.json`, `v2-bm25-only.json`, `v2-hybrid-bm25.json`, and `v2-hybrid-bm25-rerank.json`.
- Answer runs: `answers-v1.json`, `answers-v2.json`, and `answers-v1-recheck.json` (repeated runs produced identical answers and refusal outcomes).
- Manual reviews: `eval/reviews/answers-v1-review.md`, `answers-v2-review.md`, `answers-v1-flagged.md`, and `false-refusals.md`.

### 5. How to rerun

All evaluation scripts are runnable from the repository root:

- **Run retrieval evaluation**:
  ```bash
  python -m eval.run_eval --questions eval/questions.jsonl --retriever hybrid-bm25 --run-name my-v1-run
  python -m eval.run_eval --questions eval/questions_v2.jsonl --retriever hybrid-bm25 --run-name my-v2-run
  python -m eval.run_eval --questions eval/questions_v2.jsonl --retriever hybrid-bm25-rerank --run-name my-v2-rerank
  ```
- **Compare two retrieval runs**:
  ```bash
  python -m eval.compare baseline-vector-only hybrid-bm25-v1
  python -m eval.compare v2-vector-only v2-hybrid-bm25
  ```
- **Run end-to-end answer evaluation** (requires running Ollama server with `llama31-rag`):
  ```bash
  python eval/run_answer_eval.py --questions eval/questions.jsonl --run-name answers-v1-run
  python eval/run_answer_eval.py --questions eval/questions_v2.jsonl --run-name answers-v2-run
  ```
  *(To evaluate specific questions only, use `--ids q001,q002`).*
- **Generate answer report & review template**:
  ```bash
  python eval/answer_report.py eval/baselines/answers-v1.json
  ```

### 6. Known limitations

- **Small sample sizes**: With 20 answerable questions on v2, each question accounts for 5.0 percentage points on Hit@1 and Hit@5; in 15-answer review samples, one question represents 6.7 percentage points.
- **Development set bias**: The v1 set (31 answerable questions) was AI-drafted and used during iterative development, potentially favoring keyword matching.
- **Page-level hit matching**: A hit counts any chunk from an expected page, even if the specific chunk lacks the information needed to answer the question (e.g. `q002` retrieved 4 expected-page chunks in its top 5, none showing the OAuth2PasswordBearer setup).
- **Assisted manual review**: Answer correctness verdicts were first-pass drafts written with Claude and checked by the author against each cited chunk, deviating from the author-only scoring specified in the pre-registration protocol.

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
├── app/              # FastAPI application, configuration, schemas, and LLM client
├── ingest/           # Markdown loader, heading-aware chunker, and embedding pipeline
├── retrieval/        # Retrieval strategies
│   ├── vector.py     # Dense vector similarity search (pgvector HNSW)
│   ├── fulltext.py   # PostgreSQL full-text search (tsvector/tsquery)
│   ├── bm25.py       # In-memory BM25Okapi keyword search
│   ├── hybrid.py     # Reciprocal rank fusion of vector and BM25
│   └── rerank.py     # Optional cross-encoder reranker (bge-reranker-base)
├── eval/             # Evaluation harness, question sets, baselines, and reviews
│   ├── run_eval.py   # Retrieval evaluation pipeline
│   ├── compare.py    # Metric comparison across retrieval baselines
│   ├── run_answer_eval.py # End-to-end answer quality evaluation runner
│   ├── answer_report.py   # Answer metrics and manual-review templates
│   ├── questions.jsonl    # Development question set v1 (40 questions)
│   ├── questions_v2.jsonl # Held-out question set v2 (31 questions)
│   ├── PREREGISTRATION*.md# Pre-registration protocols for retrieval and answer runs
│   ├── baselines/    # Frozen retrieval and answer run outputs
│   └── reviews/      # Manual answer audits and refusal inspections
├── tests/            # Test suite for chunker, loaders, retrievers, and API
├── db/               # PostgreSQL schema and initialization scripts
├── scripts/          # Helper utilities (documentation downloader)
├── data/             # Documentation directory (downloaded via script, not committed)
├── ui/               # Not implemented (empty placeholder)
├── docker-compose.yml# Container orchestration for pgvector service
├── Modelfile         # Ollama model definition for llama31-rag
├── .env.example      # Environment variable template
├── requirements.txt  # Python package dependencies
├── README.md         # Architecture, setup instructions, and evaluation summary
├── RESULTS.md        # Comprehensive retrieval and answer evaluation benchmarks
└── FAILURES.md       # Failure cases and findings (retrieval, gate, generation)
```

## Quick Start

Requirements: Python 3.11, Docker Desktop (running), Ollama, about 8 GB free disk (the first pip install pulls PyTorch and can take 5+ minutes).

1. Copy `.env.example` to `.env` (the defaults work for local use; there is nothing to fill in):

   macOS / Linux:

   ```bash
   cp .env.example .env
   ```

   Windows:

   ```cmd
   copy .env.example .env
   ```

2. Start the PostgreSQL + pgvector container:

   ```bash
   docker compose up -d
   ```

   If port 5433 is already in use, change POSTGRES_PORT and DATABASE_URL in `.env`.

3. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   ```

   macOS / Linux:

   ```bash
   source .venv/bin/activate
   ```

   Windows:

   ```powershell
   .\.venv\Scripts\activate
   ```

4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Download FastAPI documentation (shallow clone):

   ```bash
   python scripts/download_docs.py
   ```

6. Ingest documentation into PostgreSQL:

   ```bash
   python -m ingest.run --docs data/docs
   ```

7. Set up Ollama and the custom model:

   Install Ollama, make sure Ollama is running (`ollama serve`), pull the base model, and create `llama31-rag` from the repository's Modelfile:

   ```bash
   ollama pull llama3.1:8b
   ollama create llama31-rag -f Modelfile
   ```

   *Note*: The model needs about 5 GB; on a GPU with 4 GB VRAM it partly runs on CPU, so answers take roughly 6 to 60 seconds.

8. Start the API server:

   ```bash
   python -m app.main
   ```

### First run note

The embedding model (`BAAI/bge-small-en-v1.5`) downloads automatically on first use. The optional cross-encoder reranker (`BAAI/bge-reranker-base`, about 1.1 GB) downloads only if `USE_RERANKER=true`.

Embeddings run on whichever device SentenceTransformer selects (CUDA if available, otherwise CPU); the evaluation results in RESULTS.md were produced on a machine with a 4 GB GPU. Scores can differ slightly on other hardware.

The BM25 index is built in the background at startup; /health answers immediately and the first /ask waits for the index if it is not ready.

Verified from a fresh clone on 2026-10-28: ingestion produced 124 documents and 1,117 chunks (about 4 minutes on a development machine) and the first test question returned the same answer and score as the development setup.

## Try it

Ask a question using PowerShell:

```powershell
Invoke-RestMethod -Method Post -Uri "http://localhost:8001/ask" `
  -ContentType "application/json" `
  -Body '{"query": "How do I declare optional query parameters?"}'
```

Or using curl:

```bash
curl -X POST http://localhost:8001/ask \
  -H "Content-Type: application/json" \
  -d '{"query": "How do I declare optional query parameters?"}'
```

Questions outside the documentation (for example, "What is the capital of France?") are refused without calling the model.

## Configuration

The assistant is configured via environment variables or `.env`:

| Variable | Default | Description |
|---|---|---|
| `POSTGRES_PORT` | `5433` | Host port mapped to PostgreSQL in `docker-compose.yml`. |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5433/rag_db` | PostgreSQL connection URL. |
| `EMBEDDING_DIMENSION` | `384` | Embedding vector dimension for `BAAI/bge-small-en-v1.5`. |
| `RETRIEVER` | `hybrid-bm25` | Retriever pipeline: `vector`, `hybrid-bm25`, or `hybrid-bm25-rerank`. |
| `USE_RERANKER` | `false` | Whether to enable cross-encoder reranking (`BAAI/bge-reranker-base`) over the top 20 candidates. |
| `MIN_SCORE` | `0.60` | Score gate threshold applied to `top_vector_score` across all retrievers. Queries with `top_vector_score < MIN_SCORE` are refused without invoking the LLM. |
| `RERANK_MIN_SCORE` | *unset* | Optional score gate threshold applied to `top_rerank_score` when `USE_RERANKER` is true. `RERANK_MIN_SCORE` is not set by default because the v1-derived 0.502 threshold passes 5 of 11 unanswerable questions on v2. |
| `LLM_BASE_URL` | `http://localhost:11434/v1` | Base URL for Ollama / OpenAI-compatible LLM endpoint. |
| `LLM_MODEL` | `llama31-rag` | Model name to invoke for answer generation. |
| `LLM_TIMEOUT_SECONDS` | `300` | Request timeout in seconds for LLM generation calls. |
| `APP_PORT` | `8001` | Server listening port. |
