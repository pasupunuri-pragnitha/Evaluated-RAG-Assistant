import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Set

from app.config import settings
from db.connection import get_db_connection
from retrieval.fulltext import search as fulltext_search
from retrieval.hybrid import search as hybrid_search
from retrieval.vector import get_embedder, search as vector_search

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def get_git_commit_hash() -> str:
    """Get the current HEAD git commit hash."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


def load_and_validate_questions(
    file_path: Path, valid_sources: Set[str]
) -> List[Dict[str, Any]]:
    """
    Loads eval/questions.jsonl and validates:
    - Required fields: id, question
    - Unique question IDs
    - Every expected_sources path exists in the documents table
    """
    if not file_path.exists():
        print(f"Error: Questions file '{file_path}' does not exist.", file=sys.stderr)
        sys.exit(1)

    questions: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()
    duplicate_ids: List[str] = []
    missing_sources: Dict[str, List[str]] = {}

    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            try:
                item = json.loads(line_str)
            except json.JSONDecodeError as e:
                print(f"Error on line {line_num} in '{file_path}': invalid JSON ({e})", file=sys.stderr)
                sys.exit(1)

            # Required field checks
            q_id = str(item.get("id", "")).strip()
            question_text = item.get("question", "").strip()

            if not q_id or not question_text:
                print(
                    f"Error on line {line_num}: missing required field 'id' or 'question'",
                    file=sys.stderr,
                )
                sys.exit(1)

            # Uniqueness check
            if q_id in seen_ids:
                duplicate_ids.append(q_id)
            seen_ids.add(q_id)

            # Determine answerability
            answerable = item.get("answerable")
            if answerable is None:
                # Default to true if expected_sources present and non-empty
                answerable = bool(item.get("expected_sources"))
            item["answerable"] = bool(answerable)

            # Validate expected_sources against DB documents table
            expected_sources = item.get("expected_sources", [])
            if not isinstance(expected_sources, list):
                expected_sources = [expected_sources]
            item["expected_sources"] = expected_sources

            if item["answerable"]:
                missing_for_q = [src for src in expected_sources if src not in valid_sources]
                if missing_for_q:
                    missing_sources[q_id] = missing_for_q

            questions.append(item)

    if duplicate_ids:
        print(f"Error: Duplicate question IDs found: {duplicate_ids}", file=sys.stderr)
        sys.exit(1)

    if missing_sources:
        print("Error: The following expected_sources do not exist in the documents table:", file=sys.stderr)
        for q_id, paths in missing_sources.items():
            print(f"  Question [{q_id}]: {paths}", file=sys.stderr)
        sys.exit(1)

    return questions


def compute_percentiles(values: List[float]) -> Dict[str, float]:
    """Compute summary statistics for a list of scores."""
    if not values:
        return {"count": 0, "min": 0.0, "p25": 0.0, "median": 0.0, "p75": 0.0, "max": 0.0, "mean": 0.0}
    sorted_v = sorted(values)
    n = len(sorted_v)

    def p(k: float) -> float:
        idx = int(round((n - 1) * k))
        return sorted_v[idx]

    return {
        "count": n,
        "min": round(sorted_v[0], 4),
        "p25": round(p(0.25), 4),
        "median": round(p(0.50), 4),
        "p75": round(p(0.75), 4),
        "max": round(sorted_v[-1], 4),
        "mean": round(sum(sorted_v) / n, 4),
    }


def run_evaluation(
    questions: List[Dict[str, Any]],
    retriever: str = "vector",
    k: int = 5,
    min_score: float = 0.60,
    pool: int = 50,
    rrf_k: int = 60,
    run_name: str = "baseline",
) -> Dict[str, Any]:
    embedder = get_embedder()
    embedding_device = str(embedder.model.device)

    total_answerable = 0
    total_unanswerable = 0

    hits_1 = 0
    hits_3 = 0
    hits_5 = 0
    reciprocal_ranks: List[float] = []

    answerable_top_vector_scores: List[float] = []
    unanswerable_top_vector_scores: List[float] = []

    answerable_false_refusals = 0
    unanswerable_refusals = 0

    per_question_results: List[Dict[str, Any]] = []

    # Per-type tracking for answerable questions
    type_stats: Dict[str, Dict[str, Any]] = {}

    print(
        f"Evaluating {len(questions)} questions [retriever={retriever}, k={k}, "
        f"MIN_SCORE={min_score}{f', pool={pool}, rrf_k={rrf_k}' if retriever == 'hybrid' else ''}]...\n"
    )

    with get_db_connection() as conn:
        for item in questions:
            q_id = item["id"]
            q_text = item["question"]
            q_type = item.get("type", "unknown")
            is_answerable = item["answerable"]
            expected_sources_list = item.get("expected_sources", [])
            expected_sources_set = set(expected_sources_list)

            if retriever == "vector":
                results = vector_search(query=q_text, k=k, conn=conn)
                top_vector_score = round(results[0].score, 4) if results else 0.0
                top_score = top_vector_score
            elif retriever == "fulltext":
                results = fulltext_search(query=q_text, k=k, conn=conn)
                top_score = round(results[0].score, 4) if results else 0.0
                v_res = vector_search(query=q_text, k=1, conn=conn)
                top_vector_score = round(v_res[0].score, 4) if v_res else 0.0
            elif retriever == "hybrid":
                h_res = hybrid_search(query=q_text, k=k, pool=pool, rrf_k=rrf_k, conn=conn)
                results = h_res.results
                top_vector_score = round(h_res.top_vector_score, 4)
                top_score = round(results[0].rrf_score, 6) if results else 0.0
            else:
                raise ValueError(f"Unknown retriever: {retriever}")

            gate_refused = top_vector_score < min_score

            retrieved_chunks = []
            for rank, r in enumerate(results, 1):
                chunk_dict = {
                    "rank": rank,
                    "source_path": r.source_path,
                    "title": r.title,
                    "heading_path": r.heading_path,
                    "score": round(r.score, 6 if retriever == "hybrid" else 4),
                    "is_match": r.source_path in expected_sources_set,
                }
                if hasattr(r, "vector_score"):
                    chunk_dict["vector_score"] = round(r.vector_score, 4) if r.vector_score is not None else None
                if hasattr(r, "vector_rank"):
                    chunk_dict["vector_rank"] = r.vector_rank
                if hasattr(r, "fulltext_rank"):
                    chunk_dict["fulltext_rank"] = r.fulltext_rank
                retrieved_chunks.append(chunk_dict)

            q_res: Dict[str, Any] = {
                "id": q_id,
                "type": q_type,
                "question": q_text,
                "answerable": is_answerable,
                "expected_sources": expected_sources_list,
                "top_score": top_score,
                "top_vector_score": top_vector_score,
                "gate_refused": gate_refused,
                "retrieved": retrieved_chunks,
                "first_match_rank": None,
                "reciprocal_rank": 0.0,
            }

            if is_answerable:
                total_answerable += 1
                answerable_top_vector_scores.append(top_vector_score)

                if q_type not in type_stats:
                    type_stats[q_type] = {
                        "count": 0,
                        "hits_1": 0,
                        "hits_3": 0,
                        "hits_5": 0,
                        "rr": [],
                    }
                type_stats[q_type]["count"] += 1

                if gate_refused:
                    answerable_false_refusals += 1

                first_rank = None
                for rank, r in enumerate(results, 1):
                    if r.source_path in expected_sources_set:
                        first_rank = rank
                        break

                if first_rank is not None:
                    q_res["first_match_rank"] = first_rank
                    rr = 1.0 / first_rank
                    q_res["reciprocal_rank"] = round(rr, 4)
                    reciprocal_ranks.append(rr)
                    type_stats[q_type]["rr"].append(rr)

                    if first_rank <= 1:
                        hits_1 += 1
                        type_stats[q_type]["hits_1"] += 1
                    if first_rank <= 3:
                        hits_3 += 1
                        type_stats[q_type]["hits_3"] += 1
                    if first_rank <= 5:
                        hits_5 += 1
                        type_stats[q_type]["hits_5"] += 1
                else:
                    reciprocal_ranks.append(0.0)
                    type_stats[q_type]["rr"].append(0.0)

            else:
                total_unanswerable += 1
                unanswerable_top_vector_scores.append(top_vector_score)
                if gate_refused:
                    unanswerable_refusals += 1

            per_question_results.append(q_res)

    # Metrics computation
    hit_at_1 = round(hits_1 / total_answerable, 4) if total_answerable else 0.0
    hit_at_3 = round(hits_3 / total_answerable, 4) if total_answerable else 0.0
    hit_at_5 = round(hits_5 / total_answerable, 4) if total_answerable else 0.0
    mrr = round(sum(reciprocal_ranks) / total_answerable, 4) if total_answerable else 0.0

    # Per-type metrics
    by_type_metrics: Dict[str, Dict[str, Any]] = {}
    for t_name, t_data in sorted(type_stats.items()):
        c = t_data["count"]
        by_type_metrics[t_name] = {
            "count": c,
            "hit_at_1": round(t_data["hits_1"] / c, 4) if c else 0.0,
            "hit_at_5": round(t_data["hits_5"] / c, 4) if c else 0.0,
            "mrr": round(sum(t_data["rr"]) / c, 4) if c else 0.0,
        }

    unanswerable_refusal_rate = (
        round(unanswerable_refusals / total_unanswerable, 4) if total_unanswerable else 0.0
    )
    answerable_false_refusal_rate = (
        round(answerable_false_refusals / total_answerable, 4) if total_answerable else 0.0
    )

    ans_stats = compute_percentiles(answerable_top_vector_scores)
    unans_stats = compute_percentiles(unanswerable_top_vector_scores)

    eval_output = {
        "run_name": run_name,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": get_git_commit_hash(),
        "embedding_device": embedding_device,
        "config": {
            "retriever": retriever,
            "k": k,
            "min_score": min_score,
            "pool": pool if retriever == "hybrid" else None,
            "rrf_k": rrf_k if retriever == "hybrid" else None,
            "embedding_model": settings.embedding_model_name,
            "llm_model": settings.llm_model,
        },
        "metrics": {
            "total_questions": len(questions),
            "answerable_count": total_answerable,
            "unanswerable_count": total_unanswerable,
            "hit_at_1": hit_at_1,
            "hit_at_3": hit_at_3,
            "hit_at_5": hit_at_5,
            "mrr": mrr,
            "by_type": by_type_metrics,
            "unanswerable_refusal_rate": unanswerable_refusal_rate,
            "answerable_false_refusal_rate": answerable_false_refusal_rate,
        },
        "score_distributions": {
            "answerable": ans_stats,
            "unanswerable": unans_stats,
        },
        "questions": per_question_results,
    }

    # Print Summary Tables
    print("=" * 64)
    print(f"RETRIEVAL EVALUATION RESULTS: {run_name} (retriever={retriever})")
    print("=" * 64)
    print(f"Total Questions    : {len(questions)}")
    print(f"  Answerable       : {total_answerable}")
    print(f"  Unanswerable     : {total_unanswerable}")
    print("-" * 64)
    print(f"OVERALL METRICS (Answerable, N={total_answerable}):")
    print(f"  Hit@1            : {hit_at_1:.4f} ({hits_1}/{total_answerable})")
    print(f"  Hit@3            : {hit_at_3:.4f} ({hits_3}/{total_answerable})")
    print(f"  Hit@5            : {hit_at_5:.4f} ({hits_5}/{total_answerable})")
    print(f"  MRR              : {mrr:.4f}")
    print("-" * 64)
    print("PER-TYPE METRICS (Answerable):")
    print(f"{'Question Type':<20} | {'Count':<5} | {'Hit@1':<8} | {'Hit@5':<8} | {'MRR':<8}")
    print("-" * 64)
    for t_name, tm in by_type_metrics.items():
        print(
            f"{t_name:<20} | {tm['count']:<5} | {tm['hit_at_1']:<8.4f} | {tm['hit_at_5']:<8.4f} | {tm['mrr']:<8.4f}"
        )
    print("-" * 64)
    print(f"Unanswerable Refusal Rate  (Gate Success) : {unanswerable_refusal_rate:.4f} ({unanswerable_refusals}/{total_unanswerable})")
    print(f"Answerable False-Refusal   (Gate Error)   : {answerable_false_refusal_rate:.4f} ({answerable_false_refusals}/{total_answerable})")
    print("-" * 64)
    print("SCORE DISTRIBUTION SIDE-BY-SIDE (Top Vector Score for Gate):")
    print(f"{'Statistic':<12} | {'Answerable':<12} | {'Unanswerable':<12}")
    print("-" * 42)
    for stat in ["count", "min", "p25", "median", "p75", "max", "mean"]:
        a_val = ans_stats.get(stat, 0.0)
        u_val = unans_stats.get(stat, 0.0)
        print(f"{stat:<12} | {a_val:<12} | {u_val:<12}")
    print("=" * 64)

    # 5 questions with lowest reciprocal rank among answerable
    answerable_results = [q for q in per_question_results if q["answerable"]]
    sorted_by_rr = sorted(answerable_results, key=lambda x: (x["reciprocal_rank"], -x["top_score"]))
    lowest_5 = sorted_by_rr[:5]

    print("\n5 QUESTIONS WITH LOWEST RECIPROCAL RANK:")
    print("-" * 75)
    print(f"{'ID':<6} | {'RR':<6} | {'TopScore':<8} | {'FirstMatch':<10} | {'Question'}")
    print("-" * 75)
    for q in lowest_5:
        fm = str(q["first_match_rank"]) if q["first_match_rank"] is not None else "None"
        print(f"{q['id']:<6} | {q['reciprocal_rank']:<6.4f} | {q['top_score']:<8.4f} | {fm:<10} | {q['question']}")
    print("-" * 75 + "\n")

    return eval_output


def main():
    parser = argparse.ArgumentParser(description="Evaluate retrieval baseline on questions dataset")
    parser.add_argument("--questions", type=str, default="eval/questions.jsonl", help="Path to questions.jsonl")
    parser.add_argument("--run-name", type=str, default="baseline", help="Identifier name for this evaluation run")
    parser.add_argument(
        "--retriever",
        type=str,
        choices=["vector", "fulltext", "hybrid"],
        default="vector",
        help="Retriever type: vector, fulltext, or hybrid (default: vector)",
    )
    parser.add_argument("-k", type=int, default=5, help="Number of retrieval chunks (default: 5)")
    parser.add_argument(
        "--min-score",
        type=float,
        default=settings.min_score,
        help=f"Score gate refusal threshold (default: {settings.min_score})",
    )
    parser.add_argument(
        "--pool",
        type=int,
        default=50,
        help="Retrieval candidate pool size for hybrid search (default: 50)",
    )
    parser.add_argument(
        "--rrf-k",
        type=int,
        default=60,
        help="RRF smoothing constant for hybrid search (default: 60)",
    )
    args = parser.parse_args()

    questions_file = Path(args.questions)

    # Query all valid documents source_paths from database
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT source_path FROM documents;")
            rows = cur.fetchall()
            valid_sources = {row["source_path"] for row in rows}

    questions = load_and_validate_questions(questions_file, valid_sources)

    results = run_evaluation(
        questions=questions,
        retriever=args.retriever,
        k=args.k,
        min_score=args.min_score,
        pool=args.pool,
        rrf_k=args.rrf_k,
        run_name=args.run_name,
    )

    # Write output to eval/results/<run_name>.json
    results_dir = Path("eval/results")
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / f"{args.run_name}.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    print(f"Full results saved to: {out_file}")


if __name__ == "__main__":
    main()
