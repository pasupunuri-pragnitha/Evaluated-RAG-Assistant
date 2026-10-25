import argparse
from dataclasses import asdict, dataclass
import sys
from typing import Any, Dict, List, Optional

from db.connection import get_db_connection


@dataclass
class FulltextSearchResult:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    content: str
    score: float
    fulltext_rank: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def search(query: str, k: int = 5, conn=None) -> List[FulltextSearchResult]:
    """
    Search chunks using PostgreSQL full-text search over chunks.tsv with GIN index.
    
    Builds an OR tsquery from plainto_tsquery so natural-language questions match:
        replace(plainto_tsquery('english', %s)::text, '&', '|')::tsquery
    
    Returns [] if the tsquery is empty.
    Returns results ordered by ts_rank_cd descending, with fulltext_rank (1-indexed).
    """
    if not query or not query.strip():
        return []

    close_conn = False
    if conn is None:
        conn = get_db_connection()
        close_conn = True

    try:
        with conn.cursor() as cur:
            # First extract the parsed tsquery and replace '&' with '|'
            cur.execute("SELECT plainto_tsquery('english', %s)::text AS ptq;", (query,))
            row = cur.fetchone()
            ptq = row["ptq"].strip() if row and row.get("ptq") else ""

            if not ptq:
                return []

            or_query_text = ptq.replace("&", "|")

            sql = """
                SELECT 
                    c.id::text AS chunk_id,
                    d.source_path,
                    d.title,
                    coalesce(c.heading_path, '') AS heading_path,
                    c.content,
                    ts_rank_cd(c.tsv, %s::tsquery) AS score
                FROM chunks c
                JOIN documents d ON c.document_id = d.id
                WHERE c.tsv @@ %s::tsquery
                ORDER BY score DESC
                LIMIT %s;
            """
            cur.execute(sql, (or_query_text, or_query_text, k))
            rows = cur.fetchall()

            results = [
                FulltextSearchResult(
                    chunk_id=row["chunk_id"],
                    source_path=row["source_path"],
                    title=row["title"],
                    heading_path=row["heading_path"],
                    content=row["content"],
                    score=float(row["score"]),
                    fulltext_rank=rank,
                )
                for rank, row in enumerate(rows, 1)
            ]
            return results
    finally:
        if close_conn:
            conn.close()


def main():
    parser = argparse.ArgumentParser(
        description="Search ingested documentation using PostgreSQL full-text search"
    )
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument(
        "-k", type=int, default=5, help="Number of results to return (default: 5)"
    )
    args = parser.parse_args()

    results = search(args.query, k=args.k)

    print(f"\nFulltext Query: '{args.query}'")
    print(f"Top {len(results)} results:\n")

    for res in results:
        print(f"[{res.fulltext_rank}] Score (ts_rank_cd): {res.score:.4f} | Path: {res.source_path}")
        print(f"    Section: {res.heading_path}")
        snippet = res.content.replace("\n", " ")[:140]
        print(f"    Preview: {snippet}...\n")


if __name__ == "__main__":
    main()
