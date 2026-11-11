import pytest
from db.connection import get_db_connection
from retrieval.fulltext import FulltextSearchResult, search


def test_fulltext_search_empty_queries_return_empty_list():
    assert search("") == []
    assert search("   ") == []
    assert search("\t\n") == []


def test_fulltext_search_stopwords_returns_empty_list():
    # In PostgreSQL's English text search configuration, 'the', 'a', 'an' are all stop words
    # plainto_tsquery('english', 'the a an') yields an empty tsquery
    assert search("the a an") == []


def test_fulltext_search_returns_results_with_ranks():
    """Test full-text search with ranked results.

    Inserts its own document fixture so the test passes on an empty database,
    and cleans up in a finally block.
    """
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO documents (source_path, title, version)
                VALUES (%s, %s, 1)
                RETURNING id;
                """,
                ("__test__/fulltext-fixture.md", "Fulltext Fixture"),
            )
            doc_id = cur.fetchone()["id"]

            cur.execute(
                """
                INSERT INTO chunks (
                    document_id, chunk_index, heading_path, content, token_count, embedding
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING id;
                """,
                (
                    doc_id,
                    0,
                    "Test > Optional parameters",
                    "optional query parameters " * 10,
                    30,
                    [0.0] * 384,
                ),
            )
            chunk_id = cur.fetchone()["id"]
        conn.commit()

        results = search("optional query parameters", k=3)
        assert len(results) > 0
        assert len(results) <= 3
        assert any(r.chunk_id == str(chunk_id) for r in results)
        assert any(r.source_path == "__test__/fulltext-fixture.md" for r in results)
        for i, r in enumerate(results, 1):
            assert isinstance(r, FulltextSearchResult)
            assert r.chunk_id
            assert r.source_path
            assert r.content
            assert r.fulltext_rank == i
            assert r.score > 0.0
    finally:
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "DELETE FROM documents WHERE source_path = %s;",
                    ("__test__/fulltext-fixture.md",),
                )
            conn.commit()
        finally:
            conn.close()
