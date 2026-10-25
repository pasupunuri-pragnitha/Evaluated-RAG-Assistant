from typing import List, Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database: bool
    llm_model: str
    total_documents: int
    total_chunks: int


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question to ask the RAG assistant")
    k: int = Field(default=5, ge=1, le=20, description="Number of top chunks to retrieve")


class Citation(BaseModel):
    citation_id: int
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    score: float


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: List[Citation]
