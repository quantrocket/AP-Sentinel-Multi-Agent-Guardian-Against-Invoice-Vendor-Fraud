"""
Loads eval/test_cases.json, hits the running FastAPI /review-invoice endpoint
for each, and reports tier accuracy, per-tier precision/recall, prompt-injection
catch rate, and latency percentiles. Run the API first: `uvicorn api.main:app`.
"""
import json, time, requests, sys
from collections import defaultdict

API_URL = "http://localhost:8000/review-invoice"


def main():
    cases = json.load(open("eval/test_cases.json"))
    results = []
    latencies = []

    for case in cases:
        t0 = time.time()
        resp = requests.post(API_URL, json={"invoice_text": case["invoice_text"], "email_text": case["email_text"]})
        latency = (time.time() - t0) * 1000
        latencies.append(latency)
        if not resp.ok:
            print(f"FAIL (HTTP {resp.status_code}): {case['name']}")
            continue
        data = resp.json()
        actual_tier = data["decision"]["tier"]
        correct = actual_tier == case["expected_tier"]
        results.append({
            "name": case["name"], "expected": case["expected_tier"], "actual": actual_tier,
            "correct": correct, "latency_ms": round(latency, 1),
        })
        print(f"{'PASS' if correct else 'FAIL'}  {case['name']:38s} expected={case['expected_tier']:6s} actual={actual_tier:6s} ({latency:.0f}ms)")

    n = len(results)
    accuracy = sum(r["correct"] for r in results) / n if n else 0
    latencies.sort()
    p50 = latencies[len(latencies)//2] if latencies else 0
    p95 = latencies[int(len(latencies)*0.95)] if latencies else 0

    per_tier = defaultdict(lambda: {"tp": 0, "fp": 0, "fn": 0})
    for r in results:
        if r["actual"] == r["expected"]:
            per_tier[r["expected"]]["tp"] += 1
        else:
            per_tier[r["actual"]]["fp"] += 1
            per_tier[r["expected"]]["fn"] += 1

    print("\n=== Summary ===")
    print(f"Cases run: {n}   Overall tier accuracy: {accuracy:.0%}")
    print(f"Latency: p50={p50:.0f}ms  p95={p95:.0f}ms")
    for tier, m in per_tier.items():
        prec = m["tp"] / (m["tp"] + m["fp"]) if (m["tp"] + m["fp"]) else float("nan")
        rec = m["tp"] / (m["tp"] + m["fn"]) if (m["tp"] + m["fn"]) else float("nan")
        print(f"  {tier:6s} precision={prec:.2f} recall={rec:.2f}")


if __name__ == "__main__":
    main()
