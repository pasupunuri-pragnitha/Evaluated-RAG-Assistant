import logging
import time
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from app.config import REFUSAL_MESSAGE, settings
from app.llm import LLMClient, process_answer_and_citations
from app.schemas import AskRequest, AskResponse, HealthResponse, LatencyMs, SourceItem
from db.connection import get_db_connection
from retrieval.vector import get_embedder, search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_api")

llm_client = LLMClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing vector embedder model...")
    get_embedder()
    logger.info("Warmup complete. Application ready on port %s", settings.app_port)
    yield


app = FastAPI(
    title="Evaluated RAG Assistant API",
    version="1.0.0",
    description="Production-grade RAG assistant over PostgreSQL + pgvector and Ollama llama31-rag.",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint verifying PostgreSQL and Ollama LLM connectivity."""
    db_ok = False
    total_docs = 0
    total_chunks = 0

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) as total_docs FROM documents;")
                total_docs = cur.fetchone()["total_docs"]

                cur.execute("SELECT count(*) as total_chunks FROM chunks;")
                total_chunks = cur.fetchone()["total_chunks"]
                db_ok = True
    except Exception as e:
        logger.error("Database health check error: %s", e)

    llm_ok = llm_client.check_reachability()

    if not db_ok:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database connection error",
        )

    return HealthResponse(
        status="ok",
        database=db_ok,
        llm_reachable=llm_ok,
        llm_model=settings.llm_model,
        total_documents=total_docs,
        total_chunks=total_chunks,
    )


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """
    RAG Endpoint:
    - Retrieves top-k chunks with pgvector HNSW index.
    - If top retrieval score < MIN_SCORE (0.60), short-circuits and refuses without calling LLM.
    - Queries OpenAI-compatible LLM endpoint (Ollama llama31-rag) with grounded prompt.
    - Validates citations, detects refusal, filters cited sources, and tracks latency.
    """
    start_total = time.perf_counter()

    # 1. Vector Retrieval
    start_retrieval = time.perf_counter()
    chunks = search(query=request.query, k=request.k)
    retrieval_ms = round((time.perf_counter() - start_retrieval) * 1000, 2)

    sources_retrieved = [
        SourceItem(
            index=i,
            source_path=chunk.source_path,
            title=chunk.title,
            heading_path=chunk.heading_path,
            score=round(chunk.score, 4),
        )
        for i, chunk in enumerate(chunks, 1)
    ]
    top_score = round(chunks[0].score, 4) if chunks else 0.0

    # 2. Score Gate: If top score is below threshold, refuse immediately without calling LLM
    if not chunks or top_score < settings.min_score:
        total_ms = round((time.perf_counter() - start_total) * 1000, 2)
        return AskResponse(
            query=request.query,
            answer=REFUSAL_MESSAGE,
            refused=True,
            top_score=top_score,
            sources_cited=[],
            sources_retrieved=sources_retrieved,
            warnings=[],
            latency_ms=LatencyMs(
                retrieval=retrieval_ms,
                llm=0.0,
                total=total_ms,
            ),
        )

    # 3. Check LLM Reachability
    if not llm_client.check_reachability():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM server not reachable at {settings.llm_base_url}",
        )

    # 4. LLM Generation
    start_llm = time.perf_counter()
    try:
        raw_answer = llm_client.generate_answer(query=request.query, chunks=chunks)
    except ConnectionError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"LLM server not reachable at {settings.llm_base_url}",
        )
    except Exception as e:
        logger.error("LLM generation error: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
    llm_ms = round((time.perf_counter() - start_llm) * 1000, 2)

    # 5. Citation Validation and Refusal Handling
    cleaned_answer, refused, sources_cited, warnings = process_answer_and_citations(
        raw_answer, k=request.k, sources_retrieved=sources_retrieved
    )

    total_ms = round((time.perf_counter() - start_total) * 1000, 2)

    return AskResponse(
        query=request.query,
        answer=cleaned_answer,
        refused=refused,
        top_score=top_score,
        sources_cited=sources_cited,
        sources_retrieved=sources_retrieved,
        warnings=warnings,
        latency_ms=LatencyMs(
            retrieval=retrieval_ms,
            llm=llm_ms,
            total=total_ms,
        ),
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
