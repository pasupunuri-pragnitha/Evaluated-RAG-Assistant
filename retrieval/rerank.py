import argparse
from dataclasses import asdict, dataclass
import math
import sys
import time
from typing import Any, Dict, List, NamedTuple, Optional

from sentence_transformers import CrossEncoder

from db.connection import get_db_connection
from retrieval.hybrid import search as hybrid_search


def sigmoid(logit: float) -> float:
    """Compute the numerically stable sigmoid of a logit."""
    if logit >= 0:
        return 1.0 / (1.0 + math.exp(-logit))
    else:
        z = math.exp(logit)
        return z / (1.0 + z)


# Load BAAI/bge-reranker-base with sentence-transformers CrossEncoder(max_length=512, device="cpu")
# once at module level.
cross_encoder = CrossEncoder("BAAI/bge-reranker-base", max_length=512, device="cpu")


@dataclass
class RerankResult:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    content: str
    rerank_score: float
    rerank_rank: int
    score: float  # alias to rerank_score for compatibility with downstream evaluators
    rrf_score: Optional[float] = None
    vector_score: Optional[float] = None
    vector_rank: Optional[int] = None
    fulltext_rank: Optional[int] = None
    bm25_rank: Optional[int] = None
    bm25_score: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class RerankResponse(NamedTuple):
    results: List[RerankResult]
    top_rerank_score: float
    top_vector_score: float
    rerank_latency_ms: float = 0.0


def rerank(
    query: str,
    candidates: List[Any],
    k: int = 5,
    model: Optional[CrossEncoder] = None,
    top_vector_score: Optional[float] = None,
) -> RerankResponse:
    """
    Reranks candidate chunks using the cross-encoder model.
    - Scores (query, heading_path + "\n" + content) for each candidate.
    - Sorts by score descending (ties broken by chunk_id).
    - Returns top k with rerank_score (sigmoid of logit), rerank_rank, plus earlier ranks/scores.
    - Also returns top_rerank_score (best rerank_score of the candidates) and top_vector_score.
    """
    if not candidates:
        return RerankResponse(
            results=[],
            top_rerank_score=0.0,
            top_vector_score=top_vector_score if top_vector_score is not None else 0.0,
            rerank_latency_ms=0.0,
        )

    ce = model if model is not None else cross_encoder

    # Default top_vector_score from candidates if not passed explicitly
    if top_vector_score is None:
        top_vector_score = max(
            (getattr(c, "vector_score", None) or 0.0 for c in candidates),
            default=0.0,
        )

    t0 = time.perf_counter()
    pairs = [
        (query, f"{c.heading_path}\n{c.content}")
        for c in candidates
    ]
    logits = ce.predict(pairs)
    latency_ms = (time.perf_counter() - t0) * 1000.0

    scored_items = []
    for c, logit in zip(candidates, logits):
        score_val = sigmoid(float(logit))
        scored_items.append({
            "chunk_id": c.chunk_id,
            "source_path": c.source_path,
            "title": c.title,
            "heading_path": c.heading_path,
            "content": c.content,
            "rerank_score": score_val,
            "score": score_val,
            "rrf_score": getattr(c, "rrf_score", None),
            "vector_score": getattr(c, "vector_score", None),
            "vector_rank": getattr(c, "vector_rank", None),
            "fulltext_rank": getattr(c, "fulltext_rank", None),
            "bm25_rank": getattr(c, "bm25_rank", None) or getattr(c, "fulltext_rank", None),
            "bm25_score": getattr(c, "bm25_score", None),
        })

    # Sort by score descending, ties broken deterministically by chunk_id
    sorted_items = sorted(
        scored_items,
        key=lambda item: (
            -item["rerank_score"],
            item["chunk_id"],
        ),
    )

    top_rerank_score = sorted_items[0]["rerank_score"] if sorted_items else 0.0

    top_k = []
    for rank_idx, item in enumerate(sorted_items[:k], 1):
        top_k.append(
            RerankResult(
                chunk_id=item["chunk_id"],
                source_path=item["source_path"],
                title=item["title"],
                heading_path=item["heading_path"],
                content=item["content"],
                rerank_score=item["rerank_score"],
                rerank_rank=rank_idx,
                score=item["score"],
                rrf_score=item["rrf_score"],
                vector_score=item["vector_score"],
                vector_rank=item["vector_rank"],
                fulltext_rank=item["fulltext_rank"],
                bm25_rank=item["bm25_rank"],
                bm25_score=item["bm25_score"],
            )
        )

    return RerankResponse(
        results=top_k,
        top_rerank_score=top_rerank_score,
        top_vector_score=top_vector_score,
        rerank_latency_ms=latency_ms,
    )


def search(
    query: str,
    k: int = 5,
    pool: int = 50,
    rrf_k: int = 60,
    conn=None,
) -> RerankResponse:
    """
    Candidate: hybrid-bm25 (pool=50, rrf_k=60, BM25 k1=1.5 b=0.75) top-20 reranked
    by BAAI/bge-reranker-base (CPU, max_length 512, no fine-tuning), top-5 returned.
    """
    if not query or not query.strip():
        return RerankResponse(
            results=[],
            top_rerank_score=0.0,
            top_vector_score=0.0,
            rerank_latency_ms=0.0,
        )

    hybrid_resp = hybrid_search(
        query=query,
        k=20,
        pool=pool,
        rrf_k=rrf_k,
        keyword_retriever="bm25",
        conn=conn,
    )

    return rerank(
        query=query,
        candidates=hybrid_resp.results,
        k=k,
        top_vector_score=hybrid_resp.top_vector_score,
    )


def main():
    parser = argparse.ArgumentParser(
        description="Search ingested documentation using Hybrid-BM25 + Cross-Encoder Reranker"
    )
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument(
        "-k", type=int, default=5, help="Number of final results to return (default: 5)"
    )
    parser.add_argument(
        "--pool", type=int, default=50, help="Retrieval candidate pool size for hybrid search (default: 50)"
    )
    parser.add_argument(
        "--rrf-k", type=int, default=60, help="RRF smoothing constant (default: 60)"
    )
    args = parser.parse_args()

    response = search(
        args.query,
        k=args.k,
        pool=args.pool,
        rrf_k=args.rrf_k,
    )

    print(f"\nReranked Query: '{args.query}'")
    print(f"Top Rerank Score: {response.top_rerank_score:.6f}")
    print(f"Top Vector Score: {response.top_vector_score:.4f}")
    print(f"Rerank Latency: {response.rerank_latency_ms:.2f} ms")
    print(f"Top {len(response.results)} reranked results:\n")

    for i, res in enumerate(response.results, 1):
        v_str = f"rank {res.vector_rank} (score {res.vector_score:.4f})" if res.vector_rank else "None"
        b_str = f"rank {res.bm25_rank}" if res.bm25_rank else "None"
        r_str = f"score {res.rrf_score:.6f}" if res.rrf_score is not None else "None"
        print(f"[{i}] Rerank Score: {res.rerank_score:.6f} | RRF: {r_str} | Vector: {v_str} | BM25: {b_str}")
        print(f"    Path: {res.source_path}")
        print(f"    Section: {res.heading_path}")
        snippet = res.content.replace("\n", " ")[:140]
        print(f"    Preview: {snippet}...\n")


if __name__ == "__main__":
    main()
