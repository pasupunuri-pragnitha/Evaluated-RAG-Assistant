import json
from pathlib import Path
import pytest
from eval.answer_report import compute_answer_metrics, generate_review_markdown, format_report_tables


@pytest.fixture
def sample_results_data():
    return {
        "run_name": "test-run",
        "results": [
            # Q1: Answerable, expected page in top 5, answered, cited expected page
            {
                "id": "q001",
                "question": "What is A?",
                "answerable": True,
                "expected_sources": ["docs/a.md"],
                "retrieval": [
                    {"rank": 1, "source_path": "docs/a.md", "heading_path": "A > Intro", "content": "Text A"}
                ],
                "top_vector_score": 0.85,
                "gate_refused": False,
                "llm_called": True,
                "answer": "A is awesome [1].",
                "refused": False,
                "cited_source_paths": ["docs/a.md"],
                "cited_chunks": [{"source_path": "docs/a.md", "heading_path": "A > Intro", "content": "Text A"}],
                "warnings": [],
                "latency_ms": {"retrieval": 10.0, "llm": 500.0, "total": 510.0, "rerank": None},
            },
            # Q2: Answerable, expected page in top 5, false refusal
            {
                "id": "q002",
                "question": "What is B?",
                "answerable": True,
                "expected_sources": ["docs/b.md"],
                "retrieval": [
                    {"rank": 1, "source_path": "docs/b.md", "heading_path": "B > Intro", "content": "Text B"}
                ],
                "top_vector_score": 0.65,
                "gate_refused": False,
                "llm_called": True,
                "answer": "I don't know based on the documentation.",
                "refused": True,
                "cited_source_paths": [],
                "cited_chunks": [],
                "warnings": [],
                "latency_ms": {"retrieval": 12.0, "llm": 200.0, "total": 212.0, "rerank": None},
            },
            # Q3: Answerable, expected page NOT in top 5 (retrieval miss, refused)
            {
                "id": "q003",
                "question": "What is C?",
                "answerable": True,
                "expected_sources": ["docs/c.md"],
                "retrieval": [
                    {"rank": 1, "source_path": "docs/other.md", "heading_path": "Other", "content": "Other text"}
                ],
                "top_vector_score": 0.55,
                "gate_refused": True,
                "llm_called": False,
                "answer": "I don't know based on the documentation.",
                "refused": True,
                "cited_source_paths": [],
                "cited_chunks": [],
                "warnings": [],
                "latency_ms": {"retrieval": 8.0, "llm": 0.0, "total": 8.0, "rerank": None},
            },
            # Q4: Answerable, expected page in top 5, answered, but cited unexpected source (not grounded) + warning
            {
                "id": "q004",
                "question": "What is D?",
                "answerable": True,
                "expected_sources": ["docs/d.md"],
                "retrieval": [
                    {"rank": 1, "source_path": "docs/d.md", "heading_path": "D > Intro", "content": "Text D"},
                    {"rank": 2, "source_path": "docs/misc.md", "heading_path": "Misc", "content": "Text Misc"},
                ],
                "top_vector_score": 0.78,
                "gate_refused": False,
                "llm_called": True,
                "answer": "D is here [2].",
                "refused": False,
                "cited_source_paths": ["docs/misc.md"],
                "cited_chunks": [{"source_path": "docs/misc.md", "heading_path": "Misc", "content": "Text Misc"}],
                "warnings": ["code block not found in cited sources"],
                "latency_ms": {"retrieval": 15.0, "llm": 600.0, "total": 615.0, "rerank": None},
            },
            # Q5: Unanswerable, refused
            {
                "id": "q005",
                "question": "How to make coffee?",
                "answerable": False,
                "expected_sources": [],
                "retrieval": [
                    {"rank": 1, "source_path": "docs/fastapi.md", "heading_path": "Intro", "content": "Intro"}
                ],
                "top_vector_score": 0.45,
                "gate_refused": True,
                "llm_called": False,
                "answer": "I don't know based on the documentation.",
                "refused": True,
                "cited_source_paths": [],
                "cited_chunks": [],
                "warnings": [],
                "latency_ms": {"retrieval": 5.0, "llm": 0.0, "total": 5.0, "rerank": None},
            },
            # Q6: Unanswerable, incorrectly answered (hallucination)
            {
                "id": "q006",
                "question": "How to fly?",
                "answerable": False,
                "expected_sources": [],
                "retrieval": [
                    {"rank": 1, "source_path": "docs/fastapi.md", "heading_path": "Intro", "content": "Intro"}
                ],
                "top_vector_score": 0.72,
                "gate_refused": False,
                "llm_called": True,
                "answer": "FastAPI enables flight by using flaps [1].",
                "refused": False,
                "cited_source_paths": ["docs/fastapi.md"],
                "cited_chunks": [{"source_path": "docs/fastapi.md", "heading_path": "Intro", "content": "Intro"}],
                "warnings": [],
                "latency_ms": {"retrieval": 10.0, "llm": 450.0, "total": 460.0, "rerank": None},
            },
        ],
    }


def test_compute_answer_metrics(sample_results_data):
    m = compute_answer_metrics(sample_results_data)

    assert m["total_questions"] == 6
    assert m["answerable_count"] == 4
    # Q1, Q2, Q4 have expected page in top 5
    assert m["retrievable_answerable_count"] == 3
    assert m["retrievable_answerable_rate"] == 3 / 4

    # False refusals: Q2
    assert m["false_refusal_count"] == 1
    assert m["false_refusal_rate"] == 1 / 3
    assert len(m["false_refusals"]) == 1
    assert m["false_refusals"][0]["id"] == "q002"
    assert m["false_refusals"][0]["expected_ranks"] == [1]

    # Answered retrievable-answerable: Q1, Q4
    assert m["answered_retrievable_answerable_count"] == 2
    # Page-grounded: Q1 only
    assert m["page_grounded_count"] == 1
    assert m["page_grounded_rate"] == 0.5

    # Unanswerable: Q5, Q6
    assert m["unanswerable_count"] == 2
    assert m["unanswerable_refused_count"] == 1
    assert m["unanswerable_refusal_rate"] == 0.5
    assert len(m["unanswerable_answered"]) == 1
    assert m["unanswerable_answered"][0]["id"] == "q006"

    # Warnings & Latency
    # Answered total: Q1, Q4, Q6 = 3 questions. Q4 has warning.
    assert m["answered_total_count"] == 3
    assert m["answers_with_warnings_count"] == 1
    assert m["warning_share"] == 1 / 3
    # Latencies: 510, 212, 8, 615, 5, 460 -> sum = 1810 / 6 = 301.67
    assert m["max_latency_ms"] == 615.0
    assert m["mean_latency_ms"] == round(1810 / 6, 2)


def test_generate_review_markdown(sample_results_data):
    md = generate_review_markdown(sample_results_data, max_items=15)
    # 3 answered questions: q001, q004, q006
    assert "## [q001]" in md
    assert "## [q004]" in md
    assert "## [q006]" in md
    assert "## [q002]" not in md  # Refused
    assert "## [q003]" not in md  # Refused
    assert "## [q005]" not in md  # Refused
    assert md.count("verdict: correct / partly / incorrect") == 3


def test_format_report_tables(sample_results_data):
    m = compute_answer_metrics(sample_results_data)
    text = format_report_tables(m)
    assert "Answer Evaluation Report: test-run" in text
    assert "Metric (A):" in text
    assert "Metric (B):" in text
    assert "Metric (C):" in text
    assert "Metric (D):" in text
    assert "q002" in text
    assert "q006" in text
