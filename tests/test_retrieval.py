from unittest.mock import MagicMock
import pytest
from retrieval.vector import search, SearchResult
import retrieval.vector as vector_mod


def test_search_returns_k_results_sorted_by_score(monkeypatch):
    # Mock Embedder
    mock_embedder = MagicMock()
    mock_embedder.embed_query.return_value = [0.1] * 384
    monkeypatch.setattr(vector_mod, "get_embedder", lambda: mock_embedder)

    # Mock DB Connection & Cursor
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

    # Simulated db rows sorted by score descending (as returned by order by distance asc)
    mock_rows = [
        {
            "chunk_id": "chunk-1",
            "source_path": "docs/fastapi/tutorial/first-steps.md",
            "title": "First Steps",
            "heading_path": "First Steps > First Steps",
            "content": "First steps content",
            "score": 0.88,
        },
        {
            "chunk_id": "chunk-2",
            "source_path": "docs/fastapi/tutorial/query-params.md",
            "title": "Query Parameters",
            "heading_path": "Query Parameters > Optional parameters",
            "content": "Query parameters content",
            "score": 0.82,
        },
        {
            "chunk_id": "chunk-3",
            "source_path": "docs/fastapi/tutorial/body.md",
            "title": "Request Body",
            "heading_path": "Request Body > Overview",
            "content": "Request body content",
            "score": 0.75,
        },
    ]
    mock_cursor.fetchall.return_value = mock_rows

    results = search(query="how to declare parameters", k=3, conn=mock_conn)

    assert len(results) == 3
    assert results[0].score == 0.88
    assert results[1].score == 0.82
    assert results[2].score == 0.75
    # Verify sorted best first
    assert results[0].score >= results[1].score >= results[2].score
    assert isinstance(results[0], SearchResult)
    assert results[0].source_path == "docs/fastapi/tutorial/first-steps.md"

    # Verify query vector passed to cursor
    mock_cursor.execute.assert_called()
    assert mock_embedder.embed_query.called
