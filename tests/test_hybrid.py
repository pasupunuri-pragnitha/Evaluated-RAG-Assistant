from dataclasses import dataclass
from typing import Optional
from unittest.mock import MagicMock
import pytest

from retrieval.hybrid import HybridResponse, HybridSearchResult, rrf_merge, search
import retrieval.hybrid as hybrid_mod


@dataclass
class DummyVectorResult:
    chunk_id: str
    source_path: str = "doc.md"
    title: str = "Title"
    heading_path: str = "Heading"
    content: str = "Content"
    score: float = 0.8


@dataclass
class DummyFulltextResult:
    chunk_id: str
    source_path: str = "doc.md"
    title: str = "Title"
    heading_path: str = "Heading"
    content: str = "Content"
    score: float = 1.5
    fulltext_rank: int = 1


def test_rrf_merge_order_and_dedupe():
    # Setup known lists
    # chunk-A: vector rank 1, fulltext rank 2 -> 1/61 + 1/62 = 0.016393 + 0.016129 = 0.032522
    # chunk-B: vector rank 2, fulltext rank 1 -> 1/62 + 1/61 = 0.032522
    # chunk-C: vector None,   fulltext rank 3 -> 1/63 = 0.015873
    # chunk-D: vector rank 3, fulltext None   -> 1/63 = 0.015873
    # chunk-E: vector rank 4, fulltext None   -> 1/64 = 0.015625
    vector_list = [
        DummyVectorResult(chunk_id="chunk-A", score=0.90),
        DummyVectorResult(chunk_id="chunk-B", score=0.85),
        DummyVectorResult(chunk_id="chunk-D", score=0.80),
        DummyVectorResult(chunk_id="chunk-E", score=0.75),
    ]
    fulltext_list = [
        DummyFulltextResult(chunk_id="chunk-B", fulltext_rank=1),
        DummyFulltextResult(chunk_id="chunk-A", fulltext_rank=2),
        DummyFulltextResult(chunk_id="chunk-C", fulltext_rank=3),
    ]

    merged = rrf_merge(vector_list, fulltext_list, rrf_k=60, k=5)

    assert len(merged) == 5
    # Unique chunk IDs (deduplicated)
    chunk_ids = [m.chunk_id for m in merged]
    assert len(chunk_ids) == len(set(chunk_ids))

    # Top two have combined RRF score ~ 0.032522
    assert merged[0].chunk_id in ("chunk-A", "chunk-B")
    assert merged[1].chunk_id in ("chunk-A", "chunk-B")
    assert round(merged[0].rrf_score, 5) == round(1 / 61 + 1 / 62, 5)

    # Verify both ranks and vector score are recorded on merged items
    chunk_a = next(m for m in merged if m.chunk_id == "chunk-A")
    assert chunk_a.vector_rank == 1
    assert chunk_a.vector_score == 0.90
    assert chunk_a.fulltext_rank == 2

    chunk_d = next(m for m in merged if m.chunk_id == "chunk-D")
    assert chunk_d.vector_rank == 3
    assert chunk_d.vector_score == 0.80
    assert chunk_d.fulltext_rank is None

    chunk_c = next(m for m in merged if m.chunk_id == "chunk-C")
    assert chunk_c.vector_rank is None
    assert chunk_c.vector_score is None
    assert chunk_c.fulltext_rank == 3


def test_rrf_merge_ties():
    # Item 1: vector rank 1 only -> 1/(60+1) = 1/61
    # Item 2: fulltext rank 1 only -> 1/(60+1) = 1/61
    # Both have exact same RRF score. Tie breaker prioritizes vector pool match.
    v_list = [DummyVectorResult(chunk_id="item-vec", score=0.8)]
    f_list = [DummyFulltextResult(chunk_id="item-ft", fulltext_rank=1)]

    merged = rrf_merge(v_list, f_list, rrf_k=60, k=2)

    assert len(merged) == 2
    assert merged[0].rrf_score == merged[1].rrf_score
    # Vector match preferred on score tie
    assert merged[0].chunk_id == "item-vec"
    assert merged[1].chunk_id == "item-ft"

    # Tie between two items with identical ranks: broken by chunk_id
    f_list_ties = [
        DummyFulltextResult(chunk_id="id-z", fulltext_rank=1),
        DummyFulltextResult(chunk_id="id-a", fulltext_rank=1),
    ]
    merged_ties = rrf_merge([], f_list_ties, rrf_k=60, k=2)
    assert merged_ties[0].chunk_id == "id-a"
    assert merged_ties[1].chunk_id == "id-z"


def test_hybrid_search_returns_top_vector_score(monkeypatch):
    mock_vec = [
        DummyVectorResult(chunk_id="chunk-1", score=0.8842),
        DummyVectorResult(chunk_id="chunk-2", score=0.7511),
    ]
    mock_ft = [
        DummyFulltextResult(chunk_id="chunk-1", score=2.5, fulltext_rank=1),
    ]

    monkeypatch.setattr(hybrid_mod, "vector_search", lambda query, k, conn: mock_vec)
    monkeypatch.setattr(hybrid_mod, "fulltext_search", lambda query, k, conn: mock_ft)

    resp = search("test query", k=2, pool=50, rrf_k=60)

    # Verify return type supports both named tuple and tuple unpacking
    assert isinstance(resp, HybridResponse)
    assert resp.top_vector_score == 0.8842

    results, top_vec = search("test query", k=2, pool=50, rrf_k=60)
    assert top_vec == 0.8842
    assert len(results) == 2
    assert results[0].chunk_id == "chunk-1"
