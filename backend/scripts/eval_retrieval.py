"""Measure retrieval quality on labeled question sets (no LLM calls).

Run from the backend folder:
    python scripts/eval_retrieval.py baseline
The label is saved with the result in data/eval_history.txt.
"""
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
BACKEND_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(BACKEND_ROOT))
sys.path.insert(0, str(SCRIPT_DIR))

from app.config import settings  # noqa: E402
from app.rag import load_knowledge_base  # noqa: E402
from eval_sets import EASY, HARD, NEGATIVE_FAR, NEGATIVE_NEAR  # noqa: E402

TOP_K = 3
THRESHOLD = settings.rag_min_score


def is_hit(chunk, expected_file, fragments):
    if chunk.source != expected_file:
        return False
    heading = chunk.heading.lower()
    return any(fragment.lower() in heading for fragment in fragments)


def evaluate_positive(kb, name, cases):
    ranks, top_scores = [], []
    print(f"\n--- {name} questions ({len(cases)}) ---")

    for question, expected_file, fragments in cases:
        hits = kb.search(question, TOP_K)
        rank = next(
            (i + 1 for i, (chunk, _) in enumerate(hits) if is_hit(chunk, expected_file, fragments)),
            None,
        )
        ranks.append(rank)
        top_scores.append(hits[0][1])

        if rank != 1:
            top_chunk, top_score = hits[0]
            status = f"rank {rank}" if rank else "MISS"
            print(f"[{status:>7}] {question}")
            print(f"          top result: {top_chunk.heading} ({top_score:.3f})")

    total = len(cases)
    hit1 = sum(1 for r in ranks if r == 1)
    hit3 = sum(1 for r in ranks if r is not None)
    mrr = sum(1 / r for r in ranks if r) / total
    answered = sum(1 for s in top_scores if s >= THRESHOLD)

    print(f"hit@1 {hit1}/{total} = {hit1 / total:.0%} | hit@3 {hit3}/{total} = {hit3 / total:.0%} "
          f"| MRR {mrr:.3f} | answered {answered}/{total}")
    return {"name": name, "total": total, "hit1": hit1, "hit3": hit3, "mrr": mrr,
            "answered": answered, "scores": top_scores}


def evaluate_negative(kb, name, questions):
    scores = [kb.search(question, 1)[0][1] for question in questions]
    rejected = sum(1 for s in scores if s < THRESHOLD)

    print(f"\n--- {name} negative questions ({len(questions)}) ---")
    for question, score in zip(questions, scores):
        if score >= THRESHOLD:
            print(f"[WRONGLY ANSWERED] {score:.3f}  {question}")
    print(f"rejected {rejected}/{len(questions)}")
    return {"name": name, "total": len(questions), "rejected": rejected, "scores": scores}


def main():
    label = sys.argv[1] if len(sys.argv) > 1 else "run"
    kb = load_knowledge_base()
    if kb is None:
        print("Knowledge base could not be loaded. Is the backend/knowledge folder filled?")
        sys.exit(1)

    print(f"\nChunks: {len(kb.chunks)} | top_k: {TOP_K} | min score: {THRESHOLD}")

    easy = evaluate_positive(kb, "EASY", EASY)
    hard = evaluate_positive(kb, "HARD", HARD)
    far = evaluate_negative(kb, "FAR", NEGATIVE_FAR)
    near = evaluate_negative(kb, "NEAR", NEGATIVE_NEAR)

    positive_scores = easy["scores"] + hard["scores"]
    negative_scores = far["scores"] + near["scores"]
    gap = min(positive_scores) - max(negative_scores)
    rejected = far["rejected"] + near["rejected"]
    negative_total = far["total"] + near["total"]

    print("\n=== Summary ===")
    print(f"EASY hit@1 {easy['hit1'] / easy['total']:.0%} | hit@3 {easy['hit3'] / easy['total']:.0%} | MRR {easy['mrr']:.3f}")
    print(f"HARD hit@1 {hard['hit1'] / hard['total']:.0%} | hit@3 {hard['hit3'] / hard['total']:.0%} | MRR {hard['mrr']:.3f}")
    print(f"Rejected bad questions: {rejected}/{negative_total}")
    print(f"Lowest top score on real questions : {min(positive_scores):.3f}")
    print(f"Highest top score on bad questions : {max(negative_scores):.3f}")
    print(f"Separation gap (higher is better; negative = overlap): {gap:+.3f}")

    history = BACKEND_ROOT / "data" / "eval_history.txt"
    history.parent.mkdir(parents=True, exist_ok=True)
    with history.open("a", encoding="utf-8") as file:
        file.write(
            f"{datetime.now():%Y-%m-%d %H:%M} | {label} | "
            f"easy hit@1={easy['hit1']}/{easy['total']} mrr={easy['mrr']:.3f} | "
            f"hard hit@1={hard['hit1']}/{hard['total']} hit@3={hard['hit3']}/{hard['total']} mrr={hard['mrr']:.3f} | "
            f"rejected={rejected}/{negative_total} gap={gap:+.3f}\n"
        )
    print(f"\nSaved to {history}")


if __name__ == "__main__":
    main()
