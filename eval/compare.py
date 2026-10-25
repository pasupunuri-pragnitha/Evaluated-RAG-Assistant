import argparse
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


def resolve_run_file(name: str) -> Path:
    """Resolve run name or path to a valid JSON file."""
    p = Path(name)
    if p.exists() and p.is_file():
        return p
    if not name.endswith(".json"):
        p_json = Path(f"{name}.json")
        if p_json.exists():
            return p_json

    candidates = [
        Path("eval/baselines") / (name if name.endswith(".json") else f"{name}.json"),
        Path("eval/results") / (name if name.endswith(".json") else f"{name}.json"),
    ]
    for c in candidates:
        if c.exists():
            return c

    print(f"Error: Could not find results file for '{name}'. Checked: {[str(c) for c in candidates]}", file=sys.stderr)
    sys.exit(1)


def format_delta(val: float, is_int: bool = False) -> str:
    if is_int:
        diff = int(val)
        return f"+{diff}" if diff > 0 else f"{diff}"
    diff = round(val, 4)
    if diff > 0:
        return f"+{diff:.4f}"
    elif diff < 0:
        return f"{diff:.4f}"
    else:
        return " 0.0000"


def compare_runs(baseline_path: Path, other_path: Path):
    with open(baseline_path, "r", encoding="utf-8") as f:
        base_data = json.load(f)
    with open(other_path, "r", encoding="utf-8") as f:
        other_data = json.load(f)

    base_name = base_data.get("run_name", baseline_path.stem)
    other_name = other_data.get("run_name", other_path.stem)

    base_m = base_data.get("metrics", {})
    other_m = other_data.get("metrics", {})

    print("=" * 82)
    print(f"EVALUATION COMPARISON: {base_name}  vs  {other_name}")
    print(f"  Baseline file: {baseline_path}")
    print(f"  Other file   : {other_path}")
    print("=" * 82)

    # 1. Overall Metrics Table
    print(f"{'Overall Metric':<32} | {'Baseline':<12} | {'Other':<12} | {'Delta':<12}")
    print("-" * 82)

    metrics_list = [
        ("Hit@1", "hit_at_1"),
        ("Hit@3", "hit_at_3"),
        ("Hit@5", "hit_at_5"),
        ("MRR", "mrr"),
        ("Unanswerable Refusal (Gate)", "unanswerable_refusal_rate"),
        ("Answerable False-Refusal (Gate)", "answerable_false_refusal_rate"),
    ]

    for label, key in metrics_list:
        b_val = float(base_m.get(key, 0.0))
        o_val = float(other_m.get(key, 0.0))
        delta = o_val - b_val
        print(f"{label:<32} | {b_val:<12.4f} | {o_val:<12.4f} | {format_delta(delta):<12}")
    print("-" * 82)

    # 2. Per-Type Metrics Table
    base_types = base_m.get("by_type", {})
    other_types = other_m.get("by_type", {})
    all_types = sorted(set(base_types.keys()) | set(other_types.keys()))

    if all_types:
        print("\nPER-TYPE METRICS COMPARISON (Answerable):")
        print(f"{'Question Type':<18} | {'N':<3} | {'Hit@1 (Base -> Other)':<22} | {'Hit@5 (Base -> Other)':<22} | {'MRR (Base -> Other)':<22}")
        print("-" * 98)
        for t_name in all_types:
            bt = base_types.get(t_name, {"count": 0, "hit_at_1": 0.0, "hit_at_5": 0.0, "mrr": 0.0})
            ot = other_types.get(t_name, {"count": 0, "hit_at_1": 0.0, "hit_at_5": 0.0, "mrr": 0.0})
            n = ot.get("count", bt.get("count", 0))

            h1_b, h1_o = bt.get("hit_at_1", 0.0), ot.get("hit_at_1", 0.0)
            h1_str = f"{h1_b:.4f} -> {h1_o:.4f} ({format_delta(h1_o - h1_b)})"

            h5_b, h5_o = bt.get("hit_at_5", 0.0), ot.get("hit_at_5", 0.0)
            h5_str = f"{h5_b:.4f} -> {h5_o:.4f} ({format_delta(h5_o - h5_b)})"

            mrr_b, mrr_o = bt.get("mrr", 0.0), ot.get("mrr", 0.0)
            mrr_str = f"{mrr_b:.4f} -> {mrr_o:.4f} ({format_delta(mrr_o - mrr_b)})"

            print(f"{t_name:<18} | {n:<3} | {h1_str:<22} | {h5_str:<22} | {mrr_str:<22}")
        print("-" * 98)

    # 3. Question Transitions (First-Match Rank)
    base_qs = {q["id"]: q for q in base_data.get("questions", [])}
    other_qs = {q["id"]: q for q in other_data.get("questions", [])}

    improved = []
    regressed = []
    miss_to_hit = []
    hit_to_miss = []

    for q_id, b_q in base_qs.items():
        if not b_q.get("answerable"):
            continue
        o_q = other_qs.get(q_id)
        if not o_q:
            continue

        b_rank = b_q.get("first_match_rank")  # None if miss
        o_rank = o_q.get("first_match_rank")  # None if miss

        # Effective rank for numeric comparison: None treated as 999
        b_eff = b_rank if b_rank is not None else 999
        o_eff = o_rank if o_rank is not None else 999

        if o_eff < b_eff:
            improved.append((q_id, b_rank, o_rank, b_q["question"]))
        elif o_eff > b_eff:
            regressed.append((q_id, b_rank, o_rank, b_q["question"]))

        if (b_rank is None or b_rank > 5) and (o_rank is not None and o_rank <= 5):
            miss_to_hit.append((q_id, b_rank, o_rank, b_q["question"]))
        elif (b_rank is not None and b_rank <= 5) and (o_rank is None or o_rank > 5):
            hit_to_miss.append((q_id, b_rank, o_rank, b_q["question"]))

    def rank_repr(r: Optional[int]) -> str:
        return f"Rank {r}" if r is not None else "Miss"

    print("\nQUESTION TRANSITIONS:")
    print("-" * 82)
    print(f"MISS TO HIT (Hit@5 gained: {len(miss_to_hit)} questions):")
    if miss_to_hit:
        for q_id, b_r, o_r, txt in miss_to_hit:
            print(f"  [{q_id}] {rank_repr(b_r)} -> {rank_repr(o_r)} | {txt}")
    else:
        print("  (None)")

    print(f"\nHIT TO MISS (Hit@5 lost: {len(hit_to_miss)} questions):")
    if hit_to_miss:
        for q_id, b_r, o_r, txt in hit_to_miss:
            print(f"  [{q_id}] {rank_repr(b_r)} -> {rank_repr(o_r)} | {txt}")
    else:
        print("  (None)")

    print(f"\nALL IMPROVED QUESTIONS ({len(improved)} questions):")
    if improved:
        for q_id, b_r, o_r, txt in improved:
            print(f"  [{q_id}] {rank_repr(b_r)} -> {rank_repr(o_r)} | {txt}")
    else:
        print("  (None)")

    print(f"\nALL REGRESSED QUESTIONS ({len(regressed)} questions):")
    if regressed:
        for q_id, b_r, o_r, txt in regressed:
            print(f"  [{q_id}] {rank_repr(b_r)} -> {rank_repr(o_r)} | {txt}")
    else:
        print("  (None)")
    print("=" * 82 + "\n")


def main():
    parser = argparse.ArgumentParser(description="Compare two retrieval evaluation runs")
    parser.add_argument("baseline_run", type=str, help="Baseline run name or path to baseline JSON")
    parser.add_argument("other_run", type=str, help="Other run name or path to comparison JSON")
    args = parser.parse_args()

    base_path = resolve_run_file(args.baseline_run)
    other_path = resolve_run_file(args.other_run)

    compare_runs(base_path, other_path)


if __name__ == "__main__":
    main()
