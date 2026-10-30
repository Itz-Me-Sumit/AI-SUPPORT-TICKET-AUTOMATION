"""Measure the response time of POST /api/voice/ask on a running server.

Run from the backend folder:
    python scripts/measure_latency.py https://3-107-146-58.sslip.io
"""
import json
import statistics
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import settings  # noqa: E402

BASE_URL = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")
QUESTIONS = [
    "How much does the Business plan cost?",
    "What are your support hours?",
    "How long does a refund take?",
    "Do you have a group plan?",
    "How do I reset my password?",
    "What happens if my payment fails?",
    "Is there a student discount?",
    "How do I turn on two factor authentication?",
]
RUNS = 20


def ask(question):
    request = urllib.request.Request(
        f"{BASE_URL}/api/voice/ask",
        data=json.dumps({"query": question}).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "X-Voice-Secret": settings.voice_api_secret,
            "User-Agent": "latency-test",
        },
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=60) as response:
        data = json.loads(response.read().decode("utf-8"))
    return time.perf_counter() - started, data["found"]


def main():
    print(f"Server: {BASE_URL}")
    ask(QUESTIONS[0])  # warm-up call, not counted

    times, found, errors = [], 0, 0
    for i in range(RUNS):
        try:
            seconds, was_found = ask(QUESTIONS[i % len(QUESTIONS)])
        except (urllib.error.URLError, TimeoutError) as error:
            errors += 1
            print(f"run {i + 1}: error {error}")
            continue
        times.append(seconds)
        found += was_found
        print(f"run {i + 1:>2}: {seconds:.2f}s")

    if not times:
        print("No successful calls.")
        return

    ordered = sorted(times)
    p95 = ordered[min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))]
    print(f"\ncalls: {len(times)} ok, {errors} errors, found={found}")
    print(f"median: {statistics.median(times):.2f}s | p95: {p95:.2f}s | min: {min(times):.2f}s | max: {max(times):.2f}s")
    print("Note: this includes the network round trip from your laptop to the server.")


main()
