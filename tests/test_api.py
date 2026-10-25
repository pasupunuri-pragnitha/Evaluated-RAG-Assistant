from unittest.mock import MagicMock
import pytest
from fastapi.testclient import TestClient
from app.config import REFUSAL_MESSAGE, settings
from app.main import app
from app.schemas import SourceItem
from app.llm import process_answer_and_citations
from retrieval.vector import SearchResult
import app.main as main_mod


@pytest.fixture
def client(monkeypatch):
    # Mock pre-warm embedder during lifespan
    monkeypatch.setattr(main_mod, "get_embedder", lambda: MagicMock())
    with TestClient(app) as test_client:
        yield test_client


def test_score_below_min_score_refuses_without_calling_llm(client, monkeypatch):
    # Mock search returning top score below MIN_SCORE (e.g. 0.45 < 0.60)
    low_score_chunk = SearchResult(
        chunk_id="chunk-low",
        source_path="docs/fastapi/intro.md",
        title="Intro",
        heading_path="Intro",
        content="Irrelevant text",
        score=0.45,
    )
    monkeypatch.setattr(main_mod, "search", lambda query, k: [low_score_chunk])

    # LLM mock that should NEVER be called
    mock_llm = MagicMock()
    monkeypatch.setattr(main_mod, "llm_client", mock_llm)

    response = client.post("/ask", json={"query": "What is the capital of France?", "k": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["refused"] is True
    assert data["answer"] == REFUSAL_MESSAGE
    assert data["sources_cited"] == []
    assert data["latency_ms"]["llm"] == 0.0
    # Confirm LLM was never invoked
    mock_llm.generate_answer.assert_not_called()


def test_out_of_range_citations_removed_and_flagged():
    sources_retrieved = [
        SourceItem(
            index=1,
            source_path="docs/fastapi/tutorial/params.md",
            title="Params",
            heading_path="Params > Path",
            score=0.85,
        ),
        SourceItem(
            index=2,
            source_path="docs/fastapi/tutorial/query.md",
            title="Query",
            heading_path="Query > Optional",
            score=0.75,
        ),
    ]
    # k = 2, but answer has [1] (valid) and [5] (invalid, outside 1..2)
    raw_answer = "You can declare parameters using [1] and another method [5]."
    
    cleaned, refused, cited, warnings = process_answer_and_citations(
        raw_answer, k=2, sources_retrieved=sources_retrieved
    )

    assert "[5]" not in cleaned
    assert "[1]" in cleaned
    assert refused is False
    assert len(cited) == 1
    assert cited[0].index == 1
    assert any("citation [5] outside 1..2 removed" in w for w in warnings)


def test_answer_starting_with_i_dont_know_sets_refused_true(client, monkeypatch):
    good_chunk = SearchResult(
        chunk_id="c1",
        source_path="docs/fastapi/security.md",
        title="Security",
        heading_path="Security > OAuth2",
        content="OAuth2 details",
        score=0.80,
    )
    monkeypatch.setattr(main_mod, "search", lambda query, k: [good_chunk])

    mock_llm = MagicMock()
    mock_llm.check_reachability.return_value = True
    mock_llm.generate_answer.return_value = "I don't know how to configure that specific provider."
    monkeypatch.setattr(main_mod, "llm_client", mock_llm)

    response = client.post("/ask", json={"query": "How do I configure LDAP?", "k": 5})

    assert response.status_code == 200
    data = response.json()
    assert data["refused"] is True
    assert data["answer"] == REFUSAL_MESSAGE
    assert data["sources_cited"] == []


def test_ollama_down_returns_503(client, monkeypatch):
    good_chunk = SearchResult(
        chunk_id="c1",
        source_path="docs/fastapi/tutorial.md",
        title="Tutorial",
        heading_path="Tutorial",
        content="Tutorial content",
        score=0.85,
    )
    monkeypatch.setattr(main_mod, "search", lambda query, k: [good_chunk])

    mock_llm = MagicMock()
    # LLM is down / not reachable
    mock_llm.check_reachability.return_value = False
    monkeypatch.setattr(main_mod, "llm_client", mock_llm)

    response = client.post("/ask", json={"query": "How to declare dependencies?", "k": 5})

    assert response.status_code == 503
    assert f"LLM server not reachable at {settings.llm_base_url}" in response.json()["detail"]


def test_code_grounding_warning_when_code_not_in_sources():
    sources_retrieved = [
        SourceItem(
            index=1,
            source_path="docs/fastapi/tutorial/test.md",
            title="Test",
            heading_path="Test",
            score=0.85,
        ),
    ]
    chunks = [
        SearchResult(
            chunk_id="c1",
            source_path="docs/fastapi/tutorial/test.md",
            title="Test",
            heading_path="Test",
            content="FastAPI allows you to test easily using pytest and TestClient.",
            score=0.85,
        )
    ]
    raw_answer = """Here is the testing setup according to [1]:
```python
def hallucinated_function():
    django_model_objects_all()
    execute_custom_sql_query()
```
"""
    cleaned, refused, cited, warnings = process_answer_and_citations(
        raw_answer, k=1, sources_retrieved=sources_retrieved, chunks=chunks
    )

    assert "code block not found in cited sources" in warnings


def test_health_reports_database_and_llm_reachable(client, monkeypatch):
    # Mock db connection
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_cur = MagicMock()
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.side_effect = [{"total_docs": 124}, {"total_chunks": 1117}]
    monkeypatch.setattr(main_mod, "get_db_connection", lambda: mock_conn)

    # Mock llm reachable
    mock_llm = MagicMock()
    mock_llm.check_reachability.return_value = True
    monkeypatch.setattr(main_mod, "llm_client", mock_llm)

    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["database"] is True
    assert data["llm_reachable"] is True
    assert data["total_documents"] == 124
    assert data["total_chunks"] == 1117
