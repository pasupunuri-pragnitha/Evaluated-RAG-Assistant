import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, status
from app.config import settings
from app.llm import LLMClient
from app.schemas import AskRequest, AskResponse, Citation, HealthResponse
from db.connection import get_db_connection
from retrieval.vector import get_embedder, search

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rag_api")

# Preload embedder and LLM client
llm_client = LLMClient()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Warm up the embedder model on startup
    logger.info("Initializing vector embedder model...")
    get_embedder()
    logger.info("Application startup complete. Ready to serve requests.")
    yield


app = FastAPI(
    title="Evaluated RAG Assistant API",
    version="1.0.0",
    description="Production-grade RAG assistant over PostgreSQL + pgvector and Ollama llama31-rag.",
    lifespan=lifespan,
)


@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint validating PostgreSQL connectivity and metadata."""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT count(*) as total_docs FROM documents;")
                total_docs = cur.fetchone()["total_docs"]

                cur.execute("SELECT count(*) as total_chunks FROM chunks;")
                total_chunks = cur.fetchone()["total_chunks"]

        return HealthResponse(
            status="ok",
            database=True,
            llm_model=settings.llm_model,
            total_documents=total_docs,
            total_chunks=total_chunks,
        )
    except Exception as e:
        logger.error("Health check failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {e}",
        )


@app.post("/ask", response_model=AskResponse)
def ask_question(request: AskRequest):
    """
    RAG Endpoint:
    1. Retrieves top-k chunks by vector similarity using pgvector HNSW index.
    2. Constructs grounded prompt with numbered context citations.
    3. Queries OpenAI-compatible LLM endpoint (Ollama llama31-rag).
    4. Returns answer with source citations.
    """
    try:
        chunks = search(query=request.query, k=request.k)
        answer, used_chunks = llm_client.generate_answer(
            query=request.query, chunks=chunks
        )

        citations = [
            Citation(
                citation_id=i,
                chunk_id=chunk.chunk_id,
                source_path=chunk.source_path,
                title=chunk.title,
                heading_path=chunk.heading_path,
                score=chunk.score,
            )
            for i, chunk in enumerate(used_chunks, 1)
        ]

        return AskResponse(
            query=request.query,
            answer=answer,
            citations=citations,
        )
    except Exception as e:
        logger.error("Error processing ask request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.app_host,
        port=settings.app_port,
        reload=False,
    )
