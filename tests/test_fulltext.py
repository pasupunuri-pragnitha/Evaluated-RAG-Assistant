import pytest
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
    results = search("optional query parameters", k=3)
    assert len(results) > 0
    assert len(results) <= 3
    for i, r in enumerate(results, 1):
        assert isinstance(r, FulltextSearchResult)
        assert r.chunk_id
        assert r.source_path
        assert r.content
        assert r.fulltext_rank == i
        assert r.score > 0.0
