import pytest
from retrieval.bm25 import BM25Index, tokenize, search


def test_bm25_tokenizer_stopwords_and_stemming():
    # Stopwords should be removed
    tokens_stopwords = tokenize("the is at which on for a an")
    assert tokens_stopwords == []

    # Non-alphanumeric characters split
    tokens_punct = tokenize("fastapi-users/v1.0 (test_doc)")
    assert "fastapi" in tokens_punct
    assert "user" in tokens_punct  # stemmed "users" -> "user"
    assert "v1" in tokens_punct
    assert "0" in tokens_punct
    assert "test" in tokens_punct
    assert "doc" in tokens_punct

    # Snowball stemming
    tokens = tokenize("Running optional query parameters with dependencies")
    # 'with' is stopword, 'run', 'option', 'queri', 'paramet', 'depend'
    assert "run" in tokens
    assert "option" in tokens
    assert "queri" in tokens
    assert "paramet" in tokens
    assert "depend" in tokens
    assert "with" not in tokens


def test_bm25_empty_query_returns_empty_list():
    # Empty string
    assert search("", k=5) == []
    # Whitespace only
    assert search("   \t\n  ", k=5) == []
    # Only stopwords
    assert search("the is in at and", k=5) == []


def test_bm25_deterministic_tie_break():
    # Create an index with two documents that have identical content and heading
    raw_chunks = [
        {
            "id": "chunk-zzz",
            "source_path": "path/b.md",
            "title": "Document B",
            "heading_path": "Common Heading",
            "content": "banana apple fruit",
        },
        {
            "id": "chunk-aaa",
            "source_path": "path/a.md",
            "title": "Document A",
            "heading_path": "Common Heading",
            "content": "banana apple fruit",
        },
        {
            "id": "chunk-distractor",
            "source_path": "path/c.md",
            "title": "Document C",
            "heading_path": "Distractor",
            "content": "unrelated content here",
        },
    ]

    index = BM25Index(raw_chunks=raw_chunks)
    results = index.search("banana apple", k=2)

    assert len(results) == 2
    # Exact tie on BM25 score
    assert results[0].bm25_score == results[1].bm25_score
    # Must break tie deterministically by chunk_id ascending: chunk-aaa before chunk-zzz
    assert results[0].chunk_id == "chunk-aaa"
    assert results[1].chunk_id == "chunk-zzz"
    assert results[0].bm25_rank == 1
    assert results[1].bm25_rank == 2


def test_bm25_search_result_fields():
    raw_chunks = [
        {
            "id": "c-001",
            "source_path": "test/path.md",
            "title": "Test Title",
            "heading_path": "Test Heading",
            "content": "FastAPI is a modern web framework",
        },
        {
            "id": "c-002",
            "source_path": "test/other.md",
            "title": "Other",
            "heading_path": "Other",
            "content": "something completely unrelated",
        },
        {
            "id": "c-003",
            "source_path": "test/other2.md",
            "title": "Other2",
            "heading_path": "Other2",
            "content": "another document entirely",
        },
    ]
    index = BM25Index(raw_chunks=raw_chunks)
    results = index.search("fastapi modern", k=1)

    assert len(results) == 1
    r = results[0]
    assert r.chunk_id == "c-001"
    assert r.source_path == "test/path.md"
    assert r.title == "Test Title"
    assert r.heading_path == "Test Heading"
    assert r.content == "FastAPI is a modern web framework"
    assert r.bm25_rank == 1
    assert r.bm25_score > 0
    assert r.score == r.bm25_score
