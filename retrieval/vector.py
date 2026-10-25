import argparse
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from db.connection import get_db_connection
from ingest.embedder import Embedder

# Module-level cached embedder instance
_embedder: Optional[Embedder] = None


def get_embedder() -> Embedder:
    """Load the embedding model once and reuse across requests."""
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


@dataclass
class SearchResult:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    content: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def search(query: str, k: int = 5, conn=None) -> List[SearchResult]:
    """
    Search chunks using pgvector cosine similarity with HNSW index.

    - Embeds query with BAAI/bge-small-en-v1.5 and canonical BGE query prefix.
    - Sets session hnsw.ef_search = 100 for high recall.
    - Uses cosine distance operator (<=>), converts distance to similarity (1 - distance).
    - Returns top-k SearchResult objects ordered best first.
    """
    if not query.strip():
        return []

    embedder = get_embedder()
    query_vector = embedder.embed_query(query)

    # Use existing connection if supplied, otherwise manage one
    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            # Set ef_search to 100 for improved HNSW search recall
            cur.execute("SET hnsw.ef_search = 100;")

            sql = """
                SELECT 
                    c.id::text AS chunk_id,
                    d.source_path,
                    d.title,
                    coalesce(c.heading_path, '') AS heading_path,
                    c.content,
                    (1 - (c.embedding <=> %s::vector)) AS score
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                ORDER BY c.embedding <=> %s::vector ASC
                LIMIT %s;
            """
            cur.execute(sql, (query_vector, query_vector, k))
            rows = cur.fetchall()

            results = [
                SearchResult(
                    chunk_id=row["chunk_id"],
                    source_path=row["source_path"],
                    title=row["title"],
                    heading_path=row["heading_path"],
                    content=row["content"],
                    score=float(row["score"]),
                )
                for row in rows
            ]
            return results
    finally:
        if close_conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Search ingested documentation using vector similarity"
    )
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument(
        "-k", type=int, default=5, help="Number of results to return (default: 5)"
    )
    args = parser.parse_args()

    results = search(args.query, k=args.k)

    print(f"\nQuery: '{args.query}'")
    print(f"Top {len(results)} results:\n")

    for i, res in enumerate(results, 1):
        print(f"[{i}] Score: {res.score:.4f} | Path: {res.source_path}")
        print(f"    Section: {res.heading_path}")
        snippet = res.content.replace("\n", " ")[:140]
        print(f"    Preview: {snippet}...\n")


if __name__ == "__main__":
    main()
