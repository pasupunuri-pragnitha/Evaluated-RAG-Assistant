import argparse
from dataclasses import asdict, dataclass
import sys
from typing import Any, Dict, List, NamedTuple, Optional

from db.connection import get_db_connection
from retrieval.fulltext import search as fulltext_search
from retrieval.vector import search as vector_search


@dataclass
class HybridSearchResult:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    content: str
    rrf_score: float
    score: float  # alias to rrf_score for compatibility with downstream evaluators/renderers
    vector_score: Optional[float]
    vector_rank: Optional[int]
    fulltext_rank: Optional[int]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class HybridResponse(NamedTuple):
    """
    Tuple containing the list of merged HybridSearchResult objects and top_vector_score.
    Can be unpacked as `results, top_vector_score = search(...)` or accessed via attributes.
    """
    results: List[HybridSearchResult]
    top_vector_score: float


def rrf_merge(
    vector_results: List[Any],
    fulltext_results: List[Any],
    rrf_k: int = 60,
    k: Optional[int] = 5,
) -> List[HybridSearchResult]:
    """
    Merge vector search results and full-text search results using Reciprocal Rank Fusion (RRF).

    Formula:
        RRF score = sum(1 / (rrf_k + rank))
    where rank is 1-indexed.

    Deduplicates by chunk_id. Each result carries:
      - rrf_score (and score alias)
      - vector_score (cosine similarity if in vector pool, else None)
      - vector_rank (1-indexed rank if in vector pool, else None)
      - fulltext_rank (1-indexed rank if in fulltext pool, else None)

    Ties are broken deterministically:
      1. Higher rrf_score
      2. Lower vector_rank (vector match preference)
      3. Lower fulltext_rank
      4. Lexicographical chunk_id
    """
    chunks_map: Dict[str, Dict[str, Any]] = {}

    for rank_idx, v in enumerate(vector_results, 1):
        rank = getattr(v, "vector_rank", None) or rank_idx
        c_id = v.chunk_id
        if c_id not in chunks_map:
            chunks_map[c_id] = {
                "chunk_id": c_id,
                "source_path": v.source_path,
                "title": v.title,
                "heading_path": v.heading_path,
                "content": v.content,
                "vector_score": float(v.score),
                "vector_rank": rank,
                "fulltext_rank": None,
                "rrf_score": 1.0 / (rrf_k + rank),
            }
        else:
            chunks_map[c_id]["vector_score"] = float(v.score)
            chunks_map[c_id]["vector_rank"] = rank
            chunks_map[c_id]["rrf_score"] += 1.0 / (rrf_k + rank)

    for rank_idx, f in enumerate(fulltext_results, 1):
        rank = getattr(f, "fulltext_rank", None) or rank_idx
        c_id = f.chunk_id
        if c_id not in chunks_map:
            chunks_map[c_id] = {
                "chunk_id": c_id,
                "source_path": f.source_path,
                "title": f.title,
                "heading_path": f.heading_path,
                "content": f.content,
                "vector_score": None,
                "vector_rank": None,
                "fulltext_rank": rank,
                "rrf_score": 1.0 / (rrf_k + rank),
            }
        else:
            chunks_map[c_id]["fulltext_rank"] = rank
            chunks_map[c_id]["rrf_score"] += 1.0 / (rrf_k + rank)

    sorted_items = sorted(
        chunks_map.values(),
        key=lambda item: (
            -item["rrf_score"],
            item["vector_rank"] if item["vector_rank"] is not None else 999999,
            item["fulltext_rank"] if item["fulltext_rank"] is not None else 999999,
            item["chunk_id"],
        ),
    )

    if k is not None:
        sorted_items = sorted_items[:k]

    return [
        HybridSearchResult(
            chunk_id=item["chunk_id"],
            source_path=item["source_path"],
            title=item["title"],
            heading_path=item["heading_path"],
            content=item["content"],
            rrf_score=item["rrf_score"],
            score=item["rrf_score"],
            vector_score=item["vector_score"],
            vector_rank=item["vector_rank"],
            fulltext_rank=item["fulltext_rank"],
        )
        for item in sorted_items
    ]


def search(
    query: str,
    k: int = 5,
    pool: int = 50,
    rrf_k: int = 60,
    conn=None,
) -> HybridResponse:
    """
    Perform hybrid retrieval:
      1. Fetch top `pool` from vector search
      2. Fetch top `pool` from full-text search
      3. Merge using Reciprocal Rank Fusion (RRF) with constant rrf_k
      4. Deduplicate by chunk_id and return top k
    
    Also returns top_vector_score (highest cosine similarity from vector search),
    which the refusal gate continues to use.
    """
    if not query or not query.strip():
        return HybridResponse(results=[], top_vector_score=0.0)

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        # 1. Vector Search
        vector_results = vector_search(query=query, k=pool, conn=conn)
        top_vector_score = float(vector_results[0].score) if vector_results else 0.0

        # 2. Full-Text Search
        fulltext_results = fulltext_search(query=query, k=pool, conn=conn)

        # 3. RRF Merge
        merged_results = rrf_merge(
            vector_results=vector_results,
            fulltext_results=fulltext_results,
            rrf_k=rrf_k,
            k=k,
        )

        return HybridResponse(results=merged_results, top_vector_score=top_vector_score)
    finally:
        if close_conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Search ingested documentation using Hybrid (Vector + Full-Text RRF) retrieval"
    )
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument(
        "-k", type=int, default=5, help="Number of final results to return (default: 5)"
    )
    parser.add_argument(
        "--pool", type=int, default=50, help="Retrieval candidate pool size (default: 50)"
    )
    parser.add_argument(
        "--rrf-k", type=int, default=60, help="RRF smoothing constant (default: 60)"
    )
    args = parser.parse_args()

    response = search(args.query, k=args.k, pool=args.pool, rrf_k=args.rrf_k)

    print(f"\nHybrid Query: '{args.query}'")
    print(f"Top Vector Score: {response.top_vector_score:.4f}")
    print(f"Top {len(response.results)} merged results:\n")

    for i, res in enumerate(response.results, 1):
        v_str = f"rank {res.vector_rank} (score {res.vector_score:.4f})" if res.vector_rank else "None"
        f_str = f"rank {res.fulltext_rank}" if res.fulltext_rank else "None"
        print(f"[{i}] RRF Score: {res.rrf_score:.6f} | Vector: {v_str} | Fulltext: {f_str}")
        print(f"    Path: {res.source_path}")
        print(f"    Section: {res.heading_path}")
        snippet = res.content.replace("\n", " ")[:140]
        print(f"    Preview: {snippet}...\n")


if __name__ == "__main__":
    main()
