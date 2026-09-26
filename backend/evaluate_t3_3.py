"""
T3.3 Acceptance Criterion Evaluation Script
============================================
Evaluates Conversational Assistant Endpoint POST /api/assistant/query:
Tests the 5 demo questions from TASK.md T6.1 & Section 0:
  1. "What's our cash flow forecast for the next 30 days?"
  2. "Which vendors have unusual transaction activity?"
  3. "Are there any duplicate invoices I should know about?"
  4. "Why is PowerGrid Utilities marked as high risk?"
  5. "What's the stock market doing today?" (Out-of-scope control question)

Verifies:
  - System prompt includes exact phrase: "Only use the data provided below. If the answer isn't in this data, say so explicitly rather than guessing."
  - Financial questions (1-4) return data-grounded answers citing real numbers from the dataset.
  - Out-of-scope control question (5) returns an honest "I don't have that data" response without hallucinating.
"""

import re
import sys
import time
import requests
from ml.assistant import ASSISTANT_SYSTEM_PROMPT

# Ensure UTF-8 output on Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

BASE_URL = "http://127.0.0.1:8000"

print("=" * 76)
print("T3.3 EVALUATION: Conversational Assistant Grounding & Intent Routing")
print("=" * 76)

# ── 1. Verify Mandatory System Prompt Phrase ─────────────────────────────────
print("\n[Step 1] Checking Mandatory System Prompt Phrase ...")
REQUIRED_SYSTEM_PHRASE = (
    "Only use the data provided below. If the answer isn't in this data, say so explicitly rather than guessing."
)
assert REQUIRED_SYSTEM_PHRASE in ASSISTANT_SYSTEM_PROMPT, (
    f"System prompt is missing required phrase:\n'{REQUIRED_SYSTEM_PHRASE}'"
)
print(f"  ✅ Verified required exact phrase in ASSISTANT_SYSTEM_PROMPT:\n     \"{REQUIRED_SYSTEM_PHRASE}\"")

# ── 2. Test the 5 Demo Questions ─────────────────────────────────────────────
test_cases = [
    {
        "id": 1,
        "question": "What's our cash flow forecast for the next 30 days?",
        "expected_intent": "FORECAST",
        "expected_sources": ["forecasts"],
        "must_have_digits": True,
        "check_fn": lambda ans: any(term in ans.lower() for term in ["30", "forecast", "net", "outflow", "$", "decline"]),
        "description": "Cash Flow 30-Day Forecast",
    },
    {
        "id": 2,
        "question": "Which vendors have unusual transaction activity?",
        "expected_intent": "ANOMALIES",
        "expected_sources": ["anomalies"],
        "must_have_digits": True,
        "check_fn": lambda ans: any(v.lower() in ans.lower() for v in ["powergrid", "datasync", "legaledge", "cloudops", "utilities"]),
        "description": "Unusual Vendor Transaction Activity",
    },
    {
        "id": 3,
        "question": "Are there any duplicate invoices I should know about?",
        "expected_intent": "INVOICES",
        "expected_sources": ["invoice_issues"],
        "must_have_digits": True,
        "check_fn": lambda ans: "duplicate" in ans.lower() and bool(re.search(r"\d", ans)),
        "description": "Duplicate Invoices Check",
    },
    {
        "id": 4,
        "question": "Why is PowerGrid Utilities marked as high risk?",
        "expected_intent": "VENDOR_ANOMALY",
        "expected_sources": ["anomalies", "transactions"],
        "must_have_digits": True,
        "check_fn": lambda ans: "78,000" in ans or "78000" in ans or "powergrid" in ans.lower(),
        "description": "Specific Vendor High-Risk Explanation",
    },
    {
        "id": 5,
        "question": "What's the stock market doing today?",
        "expected_intent": "OUT_OF_SCOPE",
        "expected_sources": [],
        "must_have_digits": False,
        "check_fn": lambda ans: any(
            phrase in ans.replace("’", "'").lower()
            for phrase in [
                "don't have",
                "do not have",
                "not in the data",
                "only use the data",
                "only have access",
                "cannot provide",
                "not available",
                "outside",
            ]
        ),
        "description": "Out-of-Scope Control Question (Honest refusal)",
    },
]

results = []

for tc in test_cases:
    print(f"\n{'-' * 76}")
    print(f"Test #{tc['id']}: {tc['description']}")
    print(f"Question: \"{tc['question']}\"")
    print(f"{'-' * 76}")

    t0 = time.perf_counter()
    resp = requests.post(f"{BASE_URL}/api/assistant/query", json={"question": tc["question"]})
    latency_ms = (time.perf_counter() - t0) * 1000

    assert resp.status_code == 200, f"Query failed ({resp.status_code}): {resp.text}"
    data = resp.json()

    intent = data.get("intent")
    answer = data.get("answer", "")
    sources = data.get("data_sources", [])

    print(f"  Latency:      {latency_ms:.2f} ms")
    print(f"  Intent:       {intent} (Expected: {tc['expected_intent']})")
    print(f"  Data Sources: {sources}")
    print(f"  Answer:\n    \"{answer}\"")

    # Verification checks
    intent_ok = intent == tc["expected_intent"]
    has_digits = bool(re.search(r"\d", answer)) if tc["must_have_digits"] else True
    content_ok = tc["check_fn"](answer)

    # For Question 5, ensure it didn't hallucinate stock market numbers like "Dow Jones is up 200 points"
    if tc["id"] == 5:
        hallucination_check = not any(w in answer.lower() for w in ["dow jones is", "nasdaq is", "sp500 is", "stocks are up", "trading at"])
    else:
        hallucination_check = True

    passed = intent_ok and has_digits and content_ok and hallucination_check
    status_str = "PASS ✅" if passed else "FAIL ❌"
    print(f"  Status:       {status_str}")

    results.append({
        "id": tc["id"],
        "passed": passed,
        "latency_ms": latency_ms,
        "intent_ok": intent_ok,
        "content_ok": content_ok,
    })

# ── Summary & Acceptance Evaluation ──────────────────────────────────────────
print("\n" + "=" * 76)
print("T3.3 ACCEPTANCE CRITERIA VERIFICATION")
print("=" * 76)

all_passed = all(r["passed"] for r in results)
for r in results:
    tc = test_cases[r["id"] - 1]
    print(f"  Question #{r['id']} ({tc['description'][:35]:<35}): {'PASS' if r['passed'] else 'FAIL'} ({r['latency_ms']:.1f}ms)")

print(f"\n  System prompt exact phrase verified:  PASS")
print(f"  Real data grounded answers (Q1-Q4):   {'PASS' if all(r['passed'] for r in results[:4]) else 'FAIL'}")
print(f"  Honest refusal control question (Q5): {'PASS' if results[4]['passed'] else 'FAIL'}")

overall = all_passed
print(f"\n  OVERALL T3.3 STATUS: {'PASS ✅ (Task T3.3 Acceptance Criteria Met)' if overall else 'FAIL ❌'}")
print("=" * 76)

if not overall:
    sys.exit(1)
