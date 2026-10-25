import logging
import sys
import threading
import time
from contextlib import asynccontextmanager
from typing import Any, List, Optional, Tuple
from fastapi import FastAPI, HTTPException, status
from app.config import REFUSAL_MESSAGE, settings
from app.llm import LLMClient, process_answer_and_citations
from app.schemas import AskRequest, AskResponse, HealthResponse, LatencyMs, SourceItem
from db.connection import get_db_connection
from retrieval.vector import get_embedder, search as vector_search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_api")

llm_client = LLMClient()

# Alias search for backward compatibility with tests monkeypatching main_mod.search
search = vector_search

# Threading event signaling when background BM25 index build has finished
bm25_ready_event = threading.Event()


def is_bm25_loaded() -> bool:
    """Check if BM25 index is loaded in memory without triggering a load."""
    if "retrieval.bm25" in sys.modules:
        bm25_mod = sys.modules["retrieval.bm25"]
        return getattr(bm25_mod, "_index", None) is not None
    return False


def _build_bm25_bg():
    """Build BM25 index in a background thread."""
    try:
        logger.info("Starting background BM25 index build...")
        from retrieval.bm25 import get_bm25_index

        get_bm25_index()
        logger.info("Background BM25 index build complete.")
    except Exception as e:
        logger.warning("Background BM25 index build failed or deferred: %s", e)
    finally:
        bm25_ready_event.set()


def wait_for_bm25():
    """Wait for background BM25 index build to complete if not ready yet."""
    if not is_bm25_loaded():
        logger.info("Waiting for BM25 index build to complete before retrieval...")
        bm25_ready_event.wait(timeout=60)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing vector embedder model...")
    get_embedder()

    # Build BM25 index in background thread without blocking startup
    t = threading.Thread(target=_build_bm25_bg, daemon=True)
    t.start()

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

    retriever_name = settings.retriever
    reranker_enabled = settings.use_reranker or (retriever_name == "hybrid-bm25-rerank")
    bm25_loaded = is_bm25_loaded()

    return HealthResponse(
        status="ok",
        database=db_ok,
        llm_reachable=llm_ok,
        llm_model=settings.llm_model,
        total_documents=total_docs,
        total_chunks=total_chunks,
        retriever=retriever_name,
        reranker_enabled=reranker_enabled,
        bm25_loaded=bm25_loaded,
    )


def retrieve_chunks(
    query: str,
    k: int = 5,
) -> Tuple[List[Any], float, Optional[float], Optional[float], str]:
    """
    Retrieves chunks based on settings.retriever and settings.use_reranker.
    Returns: (chunks, top_vector_score, top_rerank_score, rerank_latency_ms, effective_retriever)
    """
    retriever_name = settings.retriever
    use_reranker = settings.use_reranker or (retriever_name == "hybrid-bm25-rerank")

    # If `search` was monkeypatched in a test fixture:
    if search != vector_search:
        mocked_chunks = search(query=query, k=k)
        top_v = round(mocked_chunks[0].score, 4) if mocked_chunks else 0.0
        return mocked_chunks, top_v, None, None, retriever_name

    if use_reranker:
        retriever_name = "hybrid-bm25-rerank"
        wait_for_bm25()
        from retrieval.rerank import search as rerank_search

        r_resp = rerank_search(query=query, k=k, pool=50, rrf_k=60)
        top_v = round(r_resp.top_vector_score, 4)
        top_r = round(r_resp.top_rerank_score, 6)
        r_lat = round(r_resp.rerank_latency_ms, 2)
        return r_resp.results, top_v, top_r, r_lat, retriever_name

    elif retriever_name == "hybrid-bm25":
        wait_for_bm25()
        from retrieval.hybrid import search as hybrid_search

        h_resp = hybrid_search(query=query, k=k, pool=50, rrf_k=60, keyword_retriever="bm25")
        top_v = round(h_resp.top_vector_score, 4)
        return h_resp.results, top_v, None, None, retriever_name

    elif retriever_name == "vector":
        chunks = vector_search(query=query, k=k)
        top_v = round(chunks[0].score, 4) if chunks else 0.0
        return chunks, top_v, None, None, retriever_name

    else:
        wait_for_bm25()
        from retrieval.hybrid import search as hybrid_search

        h_resp = hybrid_search(query=query, k=k, pool=50, rrf_k=60, keyword_retriever="bm25")
        top_v = round(h_resp.top_vector_score, 4)
        return h_resp.results, top_v, None, None, retriever_name


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """
    RAG Endpoint:
    - Uses configured retriever (default: hybrid-bm25 with pool=50, rrf_k=60, k=5).
    - If USE_RERANKER is True, reranks top 20 candidates with CrossEncoder.
    - If top_vector_score < MIN_SCORE (0.60), short-circuits and refuses without calling LLM.
    - If USE_RERANKER is True and RERANK_MIN_SCORE is set, also refuses if top_rerank_score < RERANK_MIN_SCORE.
    - Queries OpenAI-compatible LLM endpoint (Ollama llama31-rag) with grounded prompt.
    - Validates citations, detects refusal, filters cited sources, and tracks latency.
    """
    start_total = time.perf_counter()

    # 1. Retrieval
    start_retrieval = time.perf_counter()
    chunks, top_vector_score, top_rerank_score, rerank_latency_ms, effective_retriever = retrieve_chunks(
        query=request.query, k=request.k
    )
    retrieval_ms = round((time.perf_counter() - start_retrieval) * 1000, 2)

    is_hybrid_or_rerank = "hybrid" in effective_retriever or "rerank" in effective_retriever

    sources_retrieved = []
    for i, chunk in enumerate(chunks, 1):
        if is_hybrid_or_rerank:
            s_score = None
            s_rrf = round(chunk.rrf_score, 6) if getattr(chunk, "rrf_score", None) is not None else round(chunk.score, 6)
            s_vec = round(chunk.vector_score, 4) if getattr(chunk, "vector_score", None) is not None else None
            s_rerank = round(chunk.rerank_score, 6) if getattr(chunk, "rerank_score", None) is not None else None
        else:
            s_score = round(chunk.score, 4)
            s_rrf = None
            s_vec = round(chunk.score, 4)
            s_rerank = None

        sources_retrieved.append(
            SourceItem(
                index=i,
                source_path=chunk.source_path,
                title=chunk.title,
                heading_path=chunk.heading_path,
                score=s_score,
                rrf_score=s_rrf,
                vector_score=s_vec,
                rerank_score=s_rerank,
            )
        )

    # 2. Refusal Gate:
    # Always check top_vector_score against min_score for every retriever
    refused = (not chunks) or (top_vector_score < settings.min_score)

    # If reranker used and rerank_min_score set, also check top_rerank_score
    if (settings.use_reranker or effective_retriever == "hybrid-bm25-rerank") and settings.rerank_min_score is not None:
        if top_rerank_score is not None and top_rerank_score < settings.rerank_min_score:
            refused = True

    if refused:
        total_ms = round((time.perf_counter() - start_total) * 1000, 2)
        return AskResponse(
            query=request.query,
            answer=REFUSAL_MESSAGE,
            refused=True,
            sources_cited=[],
            sources_retrieved=sources_retrieved,
            warnings=[],
            latency_ms=LatencyMs(
                retrieval=retrieval_ms,
                llm=0.0,
                total=total_ms,
                rerank=rerank_latency_ms,
            ),
            retriever=effective_retriever,
            top_vector_score=top_vector_score,
            top_rerank_score=top_rerank_score,
            rerank_latency_ms=rerank_latency_ms,
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
    cleaned_answer, refused_by_llm, sources_cited, warnings = process_answer_and_citations(
        raw_answer, k=request.k, sources_retrieved=sources_retrieved, chunks=chunks
    )

    total_ms = round((time.perf_counter() - start_total) * 1000, 2)

    return AskResponse(
        query=request.query,
        answer=cleaned_answer,
        refused=refused_by_llm,
        sources_cited=sources_cited,
        sources_retrieved=sources_retrieved,
        warnings=warnings,
        latency_ms=LatencyMs(
            retrieval=retrieval_ms,
            llm=llm_ms,
            total=total_ms,
            rerank=rerank_latency_ms,
        ),
        retriever=effective_retriever,
        top_vector_score=top_vector_score,
        top_rerank_score=top_rerank_score,
        rerank_latency_ms=rerank_latency_ms,
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
