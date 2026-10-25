import argparse
from dataclasses import asdict, dataclass
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

from rank_bm25 import BM25Okapi
import snowballstemmer

from db.connection import get_db_connection

# Standard Snowball / NLTK English stopwords list (alphanumeric tokens)
ENGLISH_STOPWORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", "are", "aren", "as", "at",
    "be", "because", "been", "before", "being", "below", "between", "both", "but", "by", "can", "cannot", "could",
    "couldn", "d", "did", "didn", "do", "does", "doesn", "doing", "don", "down", "during", "each", "few", "for",
    "from", "further", "had", "hadn", "has", "hasn", "have", "haven", "having", "he", "her", "here", "hers",
    "herself", "him", "himself", "his", "how", "i", "if", "in", "into", "is", "isn", "it", "its", "itself", "just",
    "ll", "m", "me", "mightn", "more", "most", "mustn", "my", "myself", "no", "nor", "not", "now", "o", "of", "off",
    "on", "once", "only", "or", "other", "our", "ours", "ourselves", "out", "over", "own", "re", "s", "same", "shan",
    "she", "should", "shouldn", "so", "some", "such", "t", "than", "that", "the", "their", "theirs", "them",
    "themselves", "then", "there", "these", "they", "this", "those", "through", "to", "too", "under", "until", "up",
    "ve", "very", "was", "wasn", "we", "were", "weren", "what", "when", "where", "which", "while", "who", "whom",
    "why", "will", "with", "won", "would", "wouldn", "y", "you", "your", "yours", "yourself", "yourselves"
})

_stemmer = snowballstemmer.stemmer("english")


def tokenize(text: str) -> List[str]:
    """
    Tokenize text:
      1. Lowercase
      2. Split on non-alphanumeric characters
      3. Remove English stopwords
      4. Stem with English snowball stemmer
    """
    if not text:
        return []
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    non_stopwords = [w for w in words if w not in ENGLISH_STOPWORDS]
    if not non_stopwords:
        return []
    return _stemmer.stemWords(non_stopwords)


@dataclass
class BM25SearchResult:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    content: str
    score: float  # alias to bm25_score for downstream consistency
    bm25_score: float
    bm25_rank: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class ChunkRecord:
    chunk_id: str
    source_path: str
    title: str
    heading_path: str
    content: str


class BM25Index:
    """In-memory BM25 index over all documentation chunks."""

    def __init__(self, conn=None, raw_chunks: Optional[List[Dict[str, Any]]] = None):
        self.chunks: List[ChunkRecord] = []
        if raw_chunks is not None:
            self._build_from_records(raw_chunks)
        else:
            self._load_chunks_and_build(conn=conn)

    def _build_from_records(self, raw_chunks: List[Dict[str, Any]]):
        corpus_tokens: List[List[str]] = []
        for row in raw_chunks:
            rec = ChunkRecord(
                chunk_id=str(row["id"] if "id" in row else row["chunk_id"]),
                source_path=row.get("source_path", ""),
                title=row.get("title", ""),
                heading_path=row.get("heading_path", "") or "",
                content=row.get("content", ""),
            )
            self.chunks.append(rec)
            index_text = f"{rec.heading_path}\n{rec.content}"
            corpus_tokens.append(tokenize(index_text))

        self.corpus_token_sets = [set(toks) for toks in corpus_tokens]
        self.bm25 = BM25Okapi(corpus_tokens, k1=1.5, b=0.75)

    def _load_chunks_and_build(self, conn=None):
        close_conn = False
        if conn is None:
            conn = get_db_connection()
            close_conn = True

        try:
            with conn.cursor() as cur:
                sql = """
                    SELECT 
                        c.id::text AS chunk_id,
                        d.source_path,
                        d.title,
                        coalesce(c.heading_path, '') AS heading_path,
                        c.content
                    FROM chunks c
                    JOIN documents d ON c.document_id = d.id
                    ORDER BY c.id ASC;
                """
                cur.execute(sql)
                rows = cur.fetchall()

                corpus_tokens: List[List[str]] = []
                for row in rows:
                    rec = ChunkRecord(
                        chunk_id=row["chunk_id"],
                        source_path=row["source_path"],
                        title=row["title"],
                        heading_path=row["heading_path"],
                        content=row["content"],
                    )
                    self.chunks.append(rec)
                    index_text = f"{rec.heading_path}\n{rec.content}"
                    corpus_tokens.append(tokenize(index_text))

                self.corpus_token_sets = [set(toks) for toks in corpus_tokens]
                # BM25Okapi default parameters: k1=1.5, b=0.75
                self.bm25 = BM25Okapi(corpus_tokens, k1=1.5, b=0.75)
        finally:
            if close_conn:
                conn.close()

    def search(self, query: str, k: int = 5) -> List[BM25SearchResult]:
        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        doc_scores = self.bm25.get_scores(query_tokens)
        query_set = set(query_tokens)

        # Pair each chunk matching at least one query token with its score
        scored: List[Tuple[ChunkRecord, float]] = [
            (self.chunks[i], float(score))
            for i, score in enumerate(doc_scores)
            if bool(self.corpus_token_sets[i] & query_set)
        ]

        if not scored:
            return []

        # Break score ties by chunk_id deterministically: (-score, chunk_id)
        scored.sort(key=lambda x: (-x[1], x[0].chunk_id))

        top_k = scored[:k]
        return [
            BM25SearchResult(
                chunk_id=chunk.chunk_id,
                source_path=chunk.source_path,
                title=chunk.title,
                heading_path=chunk.heading_path,
                content=chunk.content,
                score=score,
                bm25_score=score,
                bm25_rank=rank,
            )
            for rank, (chunk, score) in enumerate(top_k, 1)
        ]


# Module-level cached instance
_index: Optional[BM25Index] = None


def get_bm25_index(conn=None) -> BM25Index:
    global _index
    if _index is None:
        _index = BM25Index(conn=conn)
    return _index


def search(query: str, k: int = 5, conn=None) -> List[BM25SearchResult]:
    """
    Search chunks using BM25Okapi (k1=1.5, b=0.75).
    Loads all chunks into memory on first use.
    Returns [] if query has no tokens left.
    Breaks score ties deterministically by chunk_id.
    """
    idx = get_bm25_index(conn=conn)
    return idx.search(query=query, k=k)


def main():
    parser = argparse.ArgumentParser(description="Search chunks using in-memory BM25Okapi")
    parser.add_argument("query", type=str, help="Search query")
    parser.add_argument("-k", type=int, default=5, help="Number of results (default: 5)")
    args = parser.parse_args()

    results = search(args.query, k=args.k)
    print(f"\nBM25 Query: '{args.query}'")
    print(f"Top {len(results)} results:\n")
    for res in results:
        print(f"[{res.bm25_rank}] Score: {res.bm25_score:.4f} | Path: {res.source_path}")
        print(f"    Section: {res.heading_path}")
        snippet = res.content.replace("\n", " ")[:140]
        print(f"    Preview: {snippet}...\n")


if __name__ == "__main__":
    main()
