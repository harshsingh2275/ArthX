"""
ArthX T2.3 Acceptance Evaluation Script
==========================================
Verifies that every anomaly and the forecast have a non-empty,
data-referencing explanation after the explainability pipeline runs.

Acceptance criteria (from TASK.md T2.3):
  - Every anomaly returned from GET /api/analysis/anomalies has a non-empty
    explanation string that references at least one digit or the vendor name.
  - The forecast trend_summary is non-empty and data-referencing.
  - No explanation is blank, generic, or hallucinated (spot-checked).

Run:
  cd D:/ArthX/backend
  .venv\\Scripts\\python evaluate_t2_3.py
"""

import json
import os
import re
import sys
import urllib.request
import urllib.error

# Force UTF-8 output on Windows — prevents cp1252 UnicodeEncodeError when
# LLM responses contain narrow no-break spaces or other non-ASCII characters.
if sys.stdout.encoding != "utf-8":
    sys.stdout = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1)
    sys.stderr = open(sys.stderr.fileno(), mode="w", encoding="utf-8", buffering=1)

BASE_URL = "http://127.0.0.1:8000"
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"


def http_post(path: str) -> dict:
    url = BASE_URL + path
    req = urllib.request.Request(url, method="POST", data=b"")
    req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.loads(resp.read().decode())


def http_get(path: str) -> dict | list:
    url = BASE_URL + path
    with urllib.request.urlopen(url, timeout=30) as resp:
        return json.loads(resp.read().decode())


def has_grounding(text: str, vendor: str = "") -> bool:
    """Mirrors the validation logic in ml/explainer.py."""
    if not text or not text.strip():
        return False
    if re.search(r"\d", text):
        return True
    if vendor and vendor.lower() in text.lower():
        return True
    return False


def section(title: str) -> None:
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def safe_str(text: str, max_len: int = 120) -> str:
    """Truncate and replace non-ASCII chars so Windows cp1252 never chokes."""
    return text[:max_len].encode("ascii", errors="replace").decode("ascii")


def check(label: str, condition: bool, detail: str = "") -> bool:
    tag = PASS if condition else FAIL
    detail_safe = safe_str(detail) if detail else ""
    print(f"  [{tag}] {label}", f"| {detail_safe}" if detail_safe else "")
    return condition


# ─────────────────────────────────────────────────────────────────────────────
# Step 0: Verify server is up
# ─────────────────────────────────────────────────────────────────────────────
section("Step 0: Health Check")
try:
    health = http_get("/api/health")
    key_ok = health.get("groq_api_key_configured", False)
    check("Server reachable", True)
    check(
        "GROQ_API_KEY configured",
        key_ok,
        "(template fallback will be used if False)",
    )
    print(f"  LLM model    : {health.get('llm_model', 'unknown')}")
    print(f"  Explainability mode: {health.get('explainability_mode', 'unknown')}")
except Exception as e:
    check("Server reachable", False, str(e))
    print("\nERROR: Backend not running. Start with:")
    print('  .venv\\Scripts\\uvicorn main:app --host 127.0.0.1 --port 8000')
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 1: Ensure anomalies exist (run detection if needed)
# ─────────────────────────────────────────────────────────────────────────────
section("Step 1: Ensure Anomalies Exist")
anomalies_before = http_get("/api/analysis/anomalies")
if not anomalies_before:
    print("  No anomalies found — running POST /api/analysis/run first...")
    detection_result = http_post("/api/analysis/run")
    print(f"  Detection: {detection_result.get('total_anomalies_detected', 0)} anomalies found.")
    anomalies_before = http_get("/api/analysis/anomalies")

check(
    "Anomalies exist in DB",
    len(anomalies_before) > 0,
    f"{len(anomalies_before)} records",
)

# ─────────────────────────────────────────────────────────────────────────────
# Step 2: Ensure forecast exists
# ─────────────────────────────────────────────────────────────────────────────
section("Step 2: Ensure Forecast Exists")
forecast_before = http_get("/api/forecast")
if not forecast_before.get("forecast"):
    print("  No forecast found — running POST /api/forecast/run...")
    http_post("/api/forecast/run?horizon_days=30")
    forecast_before = http_get("/api/forecast")

check(
    "Forecast exists in DB",
    len(forecast_before.get("forecast", [])) > 0,
    f"{len(forecast_before.get('forecast', []))} daily points",
)

# ─────────────────────────────────────────────────────────────────────────────
# Step 3: Run the explanation pipeline
# ─────────────────────────────────────────────────────────────────────────────
section("Step 3: Run POST /api/analysis/explain")
try:
    explain_result = http_post("/api/analysis/explain?overwrite=true")
    check("Endpoint returned 200", True)
    print(f"  Response: {json.dumps(explain_result, indent=4)}")
except urllib.error.HTTPError as e:
    check("Endpoint returned 200", False, f"HTTP {e.code}: {e.read().decode()}")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────────────────────
# Step 4: Verify anomaly explanations
# ─────────────────────────────────────────────────────────────────────────────
section("Step 4: Verify Anomaly Explanations")
anomalies_after = http_get("/api/analysis/anomalies")

total = len(anomalies_after)
blank_count = 0
ungrounded_count = 0
grounded_count = 0
fallback_count = 0

print(f"\n  Checking {total} anomalies...\n")
for a in anomalies_after:
    tx_id = a.get("transaction_id")
    vendor = a.get("vendor", "")
    risk = a.get("risk_score", 0)
    expl = a.get("explanation") or ""

    is_blank = not expl.strip()
    is_grounded = has_grounding(expl, vendor)
    # Detect fallback template pattern (still valid but worth counting)
    is_fallback = expl.startswith("This transaction from") or expl.startswith("Transaction flagged")

    if is_blank:
        blank_count += 1
        print(f"  [BLANK] tx={tx_id} vendor={vendor!r}")
    elif not is_grounded:
        ungrounded_count += 1
        print(f"  [UNGROUNDED] tx={tx_id} vendor={vendor!r}  expl={expl[:80]!r}")
    else:
        grounded_count += 1
        if is_fallback:
            fallback_count += 1

    if is_grounded and risk >= 0.85:
        severity_ok = any(w in expl.lower() for w in ("highly unusual", "urgent", "immediately", "critical", "high risk"))
        if not severity_ok:
            print(f"  [{WARN}] tx={tx_id} risk={risk:.2f} but explanation lacks urgency tone: {expl[:80]!r}")

print()
all_explained = blank_count == 0
all_grounded = ungrounded_count == 0

check(
    "All anomalies have non-empty explanations",
    all_explained,
    f"{total - blank_count}/{total} filled",
)
check(
    "All explanations are data-grounded (digit or vendor name)",
    all_grounded,
    f"{grounded_count}/{total} grounded",
)
if fallback_count:
    print(f"  [{WARN}] {fallback_count}/{total} used deterministic fallback (Gemini may be offline or key missing)")

# ─────────────────────────────────────────────────────────────────────────────
# Step 5: Verify forecast trend_summary
# ─────────────────────────────────────────────────────────────────────────────
section("Step 5: Verify Forecast Trend Summary")
forecast_after = http_get("/api/forecast")
trend = forecast_after.get("trend_summary", "") or ""

is_blank_trend = not trend.strip()
is_grounded_trend = has_grounding(trend)

check("trend_summary is non-empty", not is_blank_trend, f"'{trend[:100]}...'")
check("trend_summary contains a digit or data reference", is_grounded_trend)

# ─────────────────────────────────────────────────────────────────────────────
# Step 6: Spot-check top-risk anomaly
# ─────────────────────────────────────────────────────────────────────────────
section("Step 6: Spot-Check Top-Risk Anomaly")
if anomalies_after:
    top = sorted(anomalies_after, key=lambda x: x.get("risk_score", 0), reverse=True)[0]
    print(f"  Transaction ID : {top.get('transaction_id')}")
    print(f"  Vendor         : {top.get('vendor')}")
    print(f"  Risk Score     : {top.get('risk_score')}")
    print(f"  Reason Code    : {top.get('reason_code')}")
    print(f"  Trigger        : {safe_str(top.get('trigger_metric', ''))}")
    print(f"  Explanation    :")
    print(f"    \"{safe_str(top.get('explanation', ''), max_len=300)}\"")

# ─────────────────────────────────────────────────────────────────────────────
# Final verdict
# ─────────────────────────────────────────────────────────────────────────────
section("Final Verdict")
passes = [
    all_explained,
    all_grounded,
    not is_blank_trend,
    is_grounded_trend,
]
passed = sum(passes)
total_checks = len(passes)

if passed == total_checks:
    print(f"\n  [{PASS}] T2.3 ACCEPTANCE CRITERIA MET ({passed}/{total_checks} checks pass)")
    sys.exit(0)
else:
    print(f"\n  [{FAIL}] T2.3 FAILED ({passed}/{total_checks} checks pass)")
    sys.exit(1)
