import argparse
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import subprocess
import sys
from typing import Any, Dict, List, Optional, Set

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.main import bm25_ready_event, is_bm25_loaded, process_ask
from retrieval.bm25 import get_bm25_index

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def get_git_commit_hash() -> str:
    """Return HEAD commit hash."""
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


def load_questions(file_path: Path, filter_ids: Optional[Set[str]] = None) -> List[Dict[str, Any]]:
    """Load questions from jsonl file, optionally filtering by ID."""
    if not file_path.exists():
        logger.error("Questions file '%s' does not exist.", file_path)
        sys.exit(1)

    questions = []
    with open(file_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line_str = line.strip()
            if not line_str:
                continue
            item = json.loads(line_str)
            q_id = str(item.get("id", "")).strip()
            if filter_ids and q_id not in filter_ids:
                continue
            questions.append(item)
    return questions


def main():
    parser = argparse.ArgumentParser(description="Run end-to-end answer evaluation.")
    parser.add_argument("--questions", required=True, help="Path to questions JSONL file.")
    parser.add_argument("--run-name", required=True, help="Name for this evaluation run.")
    parser.add_argument("--ids", default=None, help="Comma-separated question IDs to evaluate (optional).")
    args = parser.parse_args()

    questions_path = Path(args.questions)
    run_name = args.run_name
    filter_ids = {i.strip() for i in args.ids.split(",")} if args.ids else None

    questions = load_questions(questions_path, filter_ids=filter_ids)
    logger.info("Loaded %d questions for run '%s'.", len(questions), run_name)

    # Ensure BM25 index is loaded
    if not is_bm25_loaded():
        logger.info("Pre-building BM25 index for evaluation...")
        get_bm25_index()
        bm25_ready_event.set()
        logger.info("BM25 index ready.")

    # Results file path
    results_dir = Path(__file__).resolve().parent / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_file = results_dir / f"{run_name}.json"

    git_hash = get_git_commit_hash()
    config_dict = {
        "retriever": settings.retriever,
        "use_reranker": settings.use_reranker,
        "k": 5,
        "min_score": settings.min_score,
        "rerank_min_score": settings.rerank_min_score,
        "llm_model": settings.llm_model,
        "temperature": 0.0,
    }

    data: Dict[str, Any] = {
        "run_name": run_name,
        "questions_file": str(questions_path),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "git_commit": git_hash,
        "config": config_dict,
        "model_name": settings.llm_model,
        "results": [],
    }

    # Resume from existing results if file exists
    completed_ids: Set[str] = set()
    if out_file.exists():
        try:
            with open(out_file, "r", encoding="utf-8") as f:
                existing = json.load(f)
                data["results"] = existing.get("results", [])
                completed_ids = {r["id"] for r in data["results"]}
                logger.info("Resuming run '%s': %d questions already completed.", run_name, len(completed_ids))
        except Exception as e:
            logger.warning("Could not resume from existing results file (%s); starting fresh.", e)

    # Throwaway warm-up request (only if not already completed all questions)
    remaining_questions = [q for q in questions if q["id"] not in completed_ids]
    if remaining_questions:
        logger.info("Sending throwaway warm-up request...")
        try:
            process_ask(query="Warm-up query for documentation assistant", k=5)
            logger.info("Warm-up complete.")
        except Exception as e:
            logger.warning("Warm-up request failed: %s", e)

    for idx, q in enumerate(remaining_questions, 1):
        q_id = q["id"]
        q_text = q["question"]
        logger.info("[%d/%d] Processing %s: %s", idx, len(remaining_questions), q_id, q_text)

        resp, chunks, gate_refused, llm_called = process_ask(query=q_text, k=5)

        retrieval_records = []
        chunk_by_idx = {}
        for rank_idx, s in enumerate(resp.sources_retrieved, 1):
            matching_chunk = chunks[rank_idx - 1] if rank_idx <= len(chunks) else None
            c_text = getattr(matching_chunk, "content", "") if matching_chunk else ""
            chunk_by_idx[s.index] = c_text
            retrieval_records.append({
                "rank": rank_idx,
                "source_path": s.source_path,
                "heading_path": s.heading_path,
                "title": s.title,
                "vector_score": s.vector_score,
                "rrf_score": s.rrf_score,
                "rerank_score": s.rerank_score,
                "content": c_text,
            })

        cited_source_paths = [s.source_path for s in resp.sources_cited]
        cited_chunks = [
            {
                "index": s.index,
                "source_path": s.source_path,
                "heading_path": s.heading_path,
                "title": s.title,
                "content": chunk_by_idx.get(s.index, ""),
            }
            for s in resp.sources_cited
        ]

        lat_dict = {
            "retrieval": resp.latency_ms.retrieval,
            "llm": resp.latency_ms.llm,
            "total": resp.latency_ms.total,
            "rerank": resp.latency_ms.rerank,
        }

        result_item = {
            "id": q_id,
            "question": q_text,
            "type": q.get("type", "unknown"),
            "answerable": q.get("answerable", True),
            "expected_sources": q.get("expected_sources", []),
            "reference_answer": q.get("reference_answer", ""),
            "retrieval": retrieval_records,
            "top_vector_score": resp.top_vector_score,
            "gate_refused": gate_refused,
            "llm_called": llm_called,
            "answer": resp.answer,
            "refused": resp.refused,
            "cited_source_paths": cited_source_paths,
            "cited_chunks": cited_chunks,
            "warnings": resp.warnings,
            "latency_ms": lat_dict,
            "git_commit": git_hash,
            "config": config_dict,
            "model_name": settings.llm_model,
        }

        data["results"].append(result_item)

        # Incrementally save after every question
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    logger.info("Evaluation run '%s' finished successfully. Saved to %s", run_name, out_file)


if __name__ == "__main__":
    main()
