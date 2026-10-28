"""Compare retrieval modes (vector, hybrid, rerank) on the labeled question sets.

Run from the backend folder (no LLM calls, so it is free):
    python scripts/eval_retrieval.py compare
    python scripts/eval_retrieval.py compare --verbose     (also lists missed questions)
"""
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from app.rag import MODES, load_knowledge_base  # noqa: E402
from eval_sets import EASY, HARD, NEGATIVE_FAR, NEGATIVE_NEAR  # noqa: E402

TOP_K = 3


def is_hit(chunk, expected_file, fragments):
    if chunk.source != expected_file:
        return False
    heading = chunk.heading.lower()
    return any(fragment.lower() in heading for fragment in fragments)


def run_positive(kb, mode, cases, verbose, name):
    ranks, top_scores, misses = [], [], []
    for question, expected_file, fragments in cases:
        hits, used = kb.search_with_mode(question, TOP_K, mode)
        if used != mode:
            return None
        rank = next(
            (i + 1 for i, (chunk, _) in enumerate(hits) if is_hit(chunk, expected_file, fragments)),
            None,
        )
        ranks.append(rank)
        top_scores.append(hits[0][1])
        if rank != 1:
            misses.append((question, rank, hits[0][0].heading))

    total = len(cases)
    stats = {
        "hit1": sum(1 for r in ranks if r == 1) / total,
        "hit3": sum(1 for r in ranks if r is not None) / total,
        "mrr": sum(1 / r for r in ranks if r) / total,
        "scores": top_scores,
    }
    if verbose and misses:
        print(f"  [{mode}] {name} questions not at rank 1:")
        for question, rank, heading in misses:
            print(f"    rank {rank or 'MISS'}: {question}  (top: {heading})")
    return stats


def best_gate(positive_scores, negative_scores):
    """Best answer/reject accuracy over all thresholds, and a threshold that achieves it."""
    values = sorted(set(positive_scores + negative_scores))
    thresholds = [values[0] - 1e-6]
    thresholds += [(a + b) / 2 for a, b in zip(values, values[1:])]
    thresholds.append(values[-1] + 1e-6)

    total = len(positive_scores) + len(negative_scores)
    results = []
    for t in thresholds:
        correct = sum(1 for s in positive_scores if s >= t)
        correct += sum(1 for s in negative_scores if s < t)
        results.append((correct, t))

    best = max(correct for correct, _ in results)
    ties = [t for correct, t in results if correct == best]
    return best / total, ties[len(ties) // 2]


def main():
    label = next((a for a in sys.argv[1:] if not a.startswith("--")), "compare")
    verbose = "--verbose" in sys.argv

    kb = load_knowledge_base()
    if kb is None:
        print("Knowledge base could not be loaded.")
        sys.exit(1)

    negatives = NEGATIVE_FAR + NEGATIVE_NEAR
    print(f"\nChunks: {len(kb.chunks)} | easy: {len(EASY)} | hard: {len(HARD)} | bad questions: {len(negatives)}\n")

    rows = []
    for mode in MODES:
        easy = run_positive(kb, mode, EASY, verbose, "EASY")
        hard = run_positive(kb, mode, HARD, verbose, "HARD")
        if easy is None or hard is None:
            print(f"[{mode}] skipped (the reranker model could not be loaded)")
            continue

        negative_scores = [kb.search_with_mode(q, 1, mode)[0][0][1] for q in negatives]
        gate_accuracy, threshold = best_gate(easy["scores"] + hard["scores"], negative_scores)
        rows.append((mode, easy, hard, gate_accuracy, threshold))

    header = f"{'mode':<8} | {'EASY h@1':>8} {'h@3':>5} {'MRR':>6} | {'HARD h@1':>8} {'h@3':>5} {'MRR':>6} | {'gate acc':>8} | suggested threshold"
    print("\n" + header)
    print("-" * len(header))
    for mode, easy, hard, gate_accuracy, threshold in rows:
        print(
            f"{mode:<8} | {easy['hit1']:>8.0%} {easy['hit3']:>5.0%} {easy['mrr']:>6.3f} | "
            f"{hard['hit1']:>8.0%} {hard['hit3']:>5.0%} {hard['mrr']:>6.3f} | "
            f"{gate_accuracy:>8.0%} | {threshold:+.3f}"
        )

    history = BACKEND_ROOT / "data" / "eval_history.txt"
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as file:
        for mode, easy, hard, gate_accuracy, threshold in rows:
            file.write(
                f"{datetime.now():%Y-%m-%d %H:%M} | {label} | {mode} | "
                f"easy hit@1={easy['hit1']:.0%} mrr={easy['mrr']:.3f} | "
                f"hard hit@1={hard['hit1']:.0%} hit@3={hard['hit3']:.0%} mrr={hard['mrr']:.3f} | "
                f"gate={gate_accuracy:.0%} threshold={threshold:+.3f}\n"
            )
    print(f"\nSaved to {history}")


if __name__ == "__main__":
    main()
