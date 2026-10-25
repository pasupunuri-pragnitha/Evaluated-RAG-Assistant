import math
from unittest.mock import Mock
import pytest

from retrieval.rerank import RerankResult, rerank, sigmoid


def test_sigmoid_mapping():
    assert math.isclose(sigmoid(0.0), 0.5, abs_tol=1e-6)
    assert sigmoid(10.0) > 0.999
    assert sigmoid(-10.0) < 0.001
    assert 0.0 < sigmoid(-1.0) < 0.5 < sigmoid(1.0) < 1.0


def test_empty_candidates():
    resp = rerank("test query", [], k=5)
    assert resp.results == []
    assert resp.top_rerank_score == 0.0
    assert resp.top_vector_score == 0.0
    assert resp.rerank_latency_ms == 0.0


def test_rerank_ordering_and_tiebreaking():
    class DummyChunk:
        def __init__(self, chunk_id, heading_path, content, rrf_score, vector_score, vector_rank):
            self.chunk_id = chunk_id
            self.source_path = f"docs/{chunk_id}.md"
            self.title = f"Title {chunk_id}"
            self.heading_path = heading_path
            self.content = content
            self.rrf_score = rrf_score
            self.vector_score = vector_score
            self.vector_rank = vector_rank
            self.fulltext_rank = None
            self.bm25_rank = None
            self.bm25_score = None

    c1 = DummyChunk("c1", "Heading A", "Content A", 0.02, 0.75, 1)
    c2 = DummyChunk("c2", "Heading B", "Content B", 0.015, 0.65, 2)
    c3 = DummyChunk("c3", "Heading C", "Content C", 0.012, 0.60, 3)
    # c4 and c5 will produce a score tie to test chunk_id tie-breaking
    c4 = DummyChunk("chunk_z", "Heading Z", "Content Z", 0.01, 0.55, 4)
    c5 = DummyChunk("chunk_a", "Heading A2", "Content A2", 0.01, 0.55, 5)

    candidates = [c1, c2, c3, c4, c5]

    # Mock CrossEncoder
    # logits: c1 -> 2.0 (high), c2 -> 0.0 (medium), c3 -> -1.0 (low), c4 -> 1.0, c5 -> 1.0 (tied)
    mock_ce = Mock()
    # When predict is called with pairs
    mock_ce.predict.return_value = [2.0, 0.0, -1.0, 1.0, 1.0]

    resp = rerank(
        query="what is fastapi?",
        candidates=candidates,
        k=4,
        model=mock_ce,
        top_vector_score=0.75,
    )

    assert mock_ce.predict.called
    pairs_arg = mock_ce.predict.call_args[0][0]
    assert len(pairs_arg) == 5
    assert pairs_arg[0] == ("what is fastapi?", "Heading A\nContent A")

    # Expected score ordering:
    # 1. c1 (logit 2.0 -> sigmoid ~0.8808)
    # 2. c4 vs c5 (logit 1.0 -> sigmoid ~0.7311, tied: chunk_a beats chunk_z alphabetically)
    #    rank 2 -> c5 ("chunk_a")
    #    rank 3 -> c4 ("chunk_z")
    # 3. c2 (logit 0.0 -> sigmoid 0.5)
    # k=4 means c3 is omitted from top 4
    results = resp.results
    assert len(results) == 4
    assert [r.chunk_id for r in results] == ["c1", "chunk_a", "chunk_z", "c2"]

    # Verify ranks and scores
    assert results[0].rerank_rank == 1
    assert math.isclose(results[0].rerank_score, sigmoid(2.0), abs_tol=1e-5)
    assert results[1].rerank_rank == 2
    assert results[1].chunk_id == "chunk_a"
    assert results[2].rerank_rank == 3
    assert results[2].chunk_id == "chunk_z"
    assert results[3].rerank_rank == 4

    assert math.isclose(resp.top_rerank_score, sigmoid(2.0), abs_tol=1e-5)
    assert resp.top_vector_score == 0.75
