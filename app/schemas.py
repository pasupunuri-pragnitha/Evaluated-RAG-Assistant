from typing import List
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    database: bool
    llm_reachable: bool
    llm_model: str
    total_documents: int
    total_chunks: int


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question to ask the RAG assistant")
    k: int = Field(default=5, ge=1, le=20, description="Number of top chunks to retrieve")


class SourceItem(BaseModel):
    index: int
    source_path: str
    title: str
    heading_path: str
    score: float


class LatencyMs(BaseModel):
    retrieval: float
    llm: float
    total: float


class AskResponse(BaseModel):
    query: str
    answer: str
    refused: bool
    top_score: float
    sources_cited: List[SourceItem]
    sources_retrieved: List[SourceItem]
    warnings: List[str]
    latency_ms: LatencyMs
