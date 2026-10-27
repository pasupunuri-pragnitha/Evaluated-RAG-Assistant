import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


def compute_answer_metrics(results_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Computes metrics (A) through (D) from PREREGISTRATION_ANSWERS.md:
    (A) retrievable-answerable = answerable questions with an expected-page chunk in the top 5;
        false-refusal rate = refused / retrievable-answerable.
    (B) page-grounded rate = answered retrievable-answerable questions whose cited sources
        include an expected page / answered retrievable-answerable.
    (C) unanswerable questions: refusal rate (gate or LLM) and the list of those answered.
    (D) share of answers with any warning, and mean and max total latency.
    """
    results: List[Dict[str, Any]] = results_data.get("results", [])

    # Split into answerable and unanswerable
    answerable_questions = [q for q in results if q.get("answerable", True)]
    unanswerable_questions = [q for q in results if not q.get("answerable", True)]

    # (A) Retrievable-answerable & False-refusal rate
    retrievable_answerable: List[Dict[str, Any]] = []
    retrievable_expected_ranks: Dict[str, List[int]] = {}

    for q in answerable_questions:
        expected = set(q.get("expected_sources", []))
        top_chunks = q.get("retrieval", [])[:5]
        matching_ranks = [
            c.get("rank", idx + 1)
            for idx, c in enumerate(top_chunks)
            if c.get("source_path") in expected
        ]
        if matching_ranks:
            retrievable_answerable.append(q)
            retrievable_expected_ranks[q["id"]] = matching_ranks

    false_refusals = [q for q in retrievable_answerable if q.get("refused", False)]
    false_refusal_details = [
        {
            "id": q["id"],
            "question": q["question"],
            "top_vector_score": q.get("top_vector_score"),
            "expected_ranks": retrievable_expected_ranks.get(q["id"], []),
            "gate_refused": q.get("gate_refused", False),
            "refused": q.get("refused", True),
        }
        for q in false_refusals
    ]

    total_ans = len(answerable_questions)
    count_ra = len(retrievable_answerable)
    count_fr = len(false_refusals)
    ra_rate = (count_ra / total_ans) if total_ans > 0 else 0.0
    fr_rate = (count_fr / count_ra) if count_ra > 0 else 0.0

    # (B) Page-grounded rate
    answered_ra = [q for q in retrievable_answerable if not q.get("refused", False)]
    page_grounded: List[Dict[str, Any]] = []
    for q in answered_ra:
        expected = set(q.get("expected_sources", []))
        cited = set(q.get("cited_source_paths", []))
        if expected.intersection(cited):
            page_grounded.append(q)

    count_ara = len(answered_ra)
    count_pg = len(page_grounded)
    pg_rate = (count_pg / count_ara) if count_ara > 0 else 0.0

    # (C) Unanswerable questions: refusal rate & list of answered
    count_unans = len(unanswerable_questions)
    unans_refused = [q for q in unanswerable_questions if q.get("refused", False)]
    unans_answered = [q for q in unanswerable_questions if not q.get("refused", False)]
    unans_refusal_rate = (len(unans_refused) / count_unans) if count_unans > 0 else 0.0

    # (D) Warnings & Latency
    answered_all = [q for q in results if not q.get("refused", False)]
    answers_with_warnings = [q for q in answered_all if q.get("warnings")]
    warning_share = (len(answers_with_warnings) / len(answered_all)) if answered_all else 0.0

    all_latencies = [
        q["latency_ms"]["total"]
        for q in results
        if "latency_ms" in q and "total" in q["latency_ms"]
    ]
    mean_lat = (sum(all_latencies) / len(all_latencies)) if all_latencies else 0.0
    max_lat = max(all_latencies) if all_latencies else 0.0

    return {
        "run_name": results_data.get("run_name", "unknown"),
        "total_questions": len(results),
        "answerable_count": total_ans,
        "retrievable_answerable_count": count_ra,
        "retrievable_answerable_rate": ra_rate,
        "false_refusal_count": count_fr,
        "false_refusal_rate": fr_rate,
        "false_refusals": false_refusal_details,
        "answered_retrievable_answerable_count": count_ara,
        "page_grounded_count": count_pg,
        "page_grounded_rate": pg_rate,
        "unanswerable_count": count_unans,
        "unanswerable_refused_count": len(unans_refused),
        "unanswerable_refusal_rate": unans_refusal_rate,
        "unanswerable_answered": [
            {
                "id": q["id"],
                "question": q["question"],
                "top_vector_score": q.get("top_vector_score"),
                "answer": q.get("answer", ""),
            }
            for q in unans_answered
        ],
        "answered_total_count": len(answered_all),
        "answers_with_warnings_count": len(answers_with_warnings),
        "warning_share": warning_share,
        "mean_latency_ms": round(mean_lat, 2),
        "max_latency_ms": round(max_lat, 2),
    }


def generate_review_markdown(results_data: Dict[str, Any], max_items: int = 15) -> str:
    """Generate review markdown for up to 15 answered questions, sorted by id."""
    results: List[Dict[str, Any]] = results_data.get("results", [])
    answered = [q for q in results if not q.get("refused", False)]
    answered_sorted = sorted(answered, key=lambda x: str(x.get("id", "")))
    subset = answered_sorted[:max_items]

    run_name = results_data.get("run_name", "unknown")
    lines = [
        f"# Manual Review: {run_name}",
        "",
        f"Reviewing {len(subset)} answered questions (ordered by id).",
        "Score each question as: correct / partly / incorrect.",
        "",
    ]

    for item in subset:
        q_id = item.get("id", "")
        question = item.get("question", "")
        ref_ans = item.get("reference_answer", "").strip()
        ans = item.get("answer", "").strip()
        cited_chunks = item.get("cited_chunks", [])

        lines.append(f"## [{q_id}] {question}")
        lines.append("")
        if ref_ans:
            lines.append(f"**Reference Answer**:\n{ref_ans}\n")
        lines.append(f"**Generated Answer**:\n{ans}\n")
        lines.append("**Cited Sources & Chunk Content**:")

        if not cited_chunks:
            lines.append("*(No cited sources)*")
        else:
            for c in cited_chunks:
                s_path = c.get("source_path", "")
                h_path = c.get("heading_path", "")
                content = c.get("content", "").strip()
                lines.append(f"- **[{s_path} > {h_path}]**:\n```\n{content}\n```")

        lines.append("")
        lines.append("verdict: correct / partly / incorrect")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def format_report_tables(m: Dict[str, Any]) -> str:
    """Format metrics into readable text tables."""
    lines = []
    lines.append(f"============================================================")
    lines.append(f"Answer Evaluation Report: {m['run_name']}")
    lines.append(f"============================================================")
    lines.append(f"Total questions evaluated: {m['total_questions']}")
    lines.append("")
    lines.append(f"Metric (A): Retrievable-Answerable & False Refusals")
    lines.append(f"------------------------------------------------------------")
    lines.append(
        f"Answerable questions:              {m['answerable_count']}"
    )
    lines.append(
        f"Retrievable-answerable (in top 5): {m['retrievable_answerable_count']}/{m['answerable_count']} ({m['retrievable_answerable_rate']*100:.1f}%)"
    )
    lines.append(
        f"False refusals:                    {m['false_refusal_count']}/{m['retrievable_answerable_count']} ({m['false_refusal_rate']*100:.1f}%)"
    )
    if m["false_refusals"]:
        lines.append("False refusal questions:")
        for fr in m["false_refusals"]:
            ranks_str = ", ".join(f"rank {r}" for r in fr["expected_ranks"])
            lines.append(
                f"  - [{fr['id']}] \"{fr['question']}\" | top_vector_score: {fr['top_vector_score']} | expected chunk: {ranks_str}"
            )
    else:
        lines.append("  (None)")
    lines.append("")

    lines.append(f"Metric (B): Page-Grounded Rate")
    lines.append(f"------------------------------------------------------------")
    lines.append(
        f"Answered retrievable-answerable:   {m['answered_retrievable_answerable_count']}"
    )
    lines.append(
        f"Page-grounded answers:             {m['page_grounded_count']}/{m['answered_retrievable_answerable_count']} ({m['page_grounded_rate']*100:.1f}%)"
    )
    lines.append("")

    lines.append(f"Metric (C): Unanswerable Questions")
    lines.append(f"------------------------------------------------------------")
    lines.append(
        f"Total unanswerable questions:      {m['unanswerable_count']}"
    )
    lines.append(
        f"Refused (gate or LLM):             {m['unanswerable_refused_count']}/{m['unanswerable_count']} ({m['unanswerable_refusal_rate']*100:.1f}%)"
    )
    if m["unanswerable_answered"]:
        lines.append("Unanswerable questions answered:")
        for ua in m["unanswerable_answered"]:
            lines.append(
                f"  - [{ua['id']}] \"{ua['question']}\" | top_vector_score: {ua['top_vector_score']}"
            )
            # Truncate answer preview to 120 chars
            preview = ua['answer'].replace("\n", " ")[:120]
            lines.append(f"    Answer preview: {preview}...")
    else:
        lines.append("  (All unanswerable questions were refused)")
    lines.append("")

    lines.append(f"Metric (D): Warnings & Latency")
    lines.append(f"------------------------------------------------------------")
    lines.append(
        f"Answers with any warning:          {m['answers_with_warnings_count']}/{m['answered_total_count']} ({m['warning_share']*100:.1f}%)"
    )
    lines.append(
        f"Total latency (mean):              {m['mean_latency_ms']} ms"
    )
    lines.append(
        f"Total latency (max):               {m['max_latency_ms']} ms"
    )
    lines.append(f"============================================================")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Generate answer evaluation report.")
    parser.add_argument("results_file", nargs="?", help="Path to results JSON file.")
    parser.add_argument("--results", help="Alternative flag for results JSON file path.")
    parser.add_argument("--max-review", type=int, default=15, help="Max answered questions for manual review file.")
    args = parser.parse_args()

    target_path_str = args.results or args.results_file
    if not target_path_str:
        print("Error: Please provide a results JSON file.", file=sys.stderr)
        sys.exit(1)

    results_file = Path(target_path_str)
    if not results_file.exists():
        print(f"Error: Results file '{results_file}' does not exist.", file=sys.stderr)
        sys.exit(1)

    with open(results_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    metrics = compute_answer_metrics(data)
    report_text = format_report_tables(metrics)
    print(report_text)

    # Write review markdown
    run_name = data.get("run_name") or results_file.stem
    review_path = results_file.parent / f"{run_name}-review.md"
    review_content = generate_review_markdown(data, max_items=args.max_review)
    with open(review_path, "w", encoding="utf-8") as f:
        f.write(review_content)
    print(f"\nWrote manual review template to: {review_path}")


if __name__ == "__main__":
    main()
