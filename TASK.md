# TASK.md — ArthX Execution Roadmap
### For Google Antigravity (Gemini/Claude models). Execute in order unless marked [PARALLEL].

This file is intentionally detailed. Every task has an **acceptance criterion** — don't mark a task done until its criterion is met. Vague completion ("it runs") is not acceptable for 🎯 tasks.

**Legend:**
- 🔴 Critical Path — blocks everything downstream
- ⚡ Parallelizable — can run alongside other tasks in the same phase
- 🎯 Demo-Critical — must work flawlessly live, no exceptions
- ✂️ Cut if behind schedule
- 🧠 Claude Code escalation point
- ⭐ Standout/differentiator — not required for a working MVP, but what separates a top submission from an average one. Only attempt after all 🔴/🎯 tasks in every phase are done.

---

## 0. Demo Narrative (read this before writing any code)

Every task below serves one 3-minute demo story. Keep this in mind so implementation choices support it, not just "feature completeness":

1. **Hook:** "Finance teams drown in manual review and only catch fraud after the money's gone." (10s)
2. **Ingest:** Show real transaction/invoice data flowing in. (15s)
3. **Detect:** Dashboard lights up with 3–5 flagged anomalies — each with a specific, numeric explanation. (30s)
4. **Forecast:** Cash flow chart shows a predicted dip 3 weeks out, with confidence band. (20s)
5. **Connect the dots (⭐ differentiator):** One flagged anomaly is shown to *directly affect* the cash flow forecast — e.g., "This duplicate payment of $12,400 is inflating your predicted outflow." This is the single best "wow" moment — build toward it.
6. **Ask the assistant:** Live, unscripted-feeling question typed into chat, answered with real numbers from the data. (30s)
7. **Close:** "Every number you just saw came with its own explanation. Nothing was a black box." (10s)

If a task doesn't serve one of these beats, it's lower priority than a task that does.

---

## 1. Standout Differentiators (⭐ — build only after core path is solid)

Call these out explicitly to Antigravity so effort isn't wasted on generic polish instead of these:

- ⭐ **Anomaly → Forecast Impact Linking:** When an anomaly is flagged, compute and display how much it shifts the cash flow forecast if excluded (e.g., "excluding this transaction changes the 30-day forecast by $X"). This is the single highest-impact differentiator — it shows the system *reasons across features*, not just runs isolated models.
- ⭐ **Confidence-calibrated explanations:** Explanation text changes tone/certainty based on the anomaly score (e.g., score 0.95 → "highly unusual"; score 0.6 → "worth a second look"). Shows nuance, not binary flag/no-flag thinking.
- ⭐ **Vendor risk profile mini-view:** Clicking a flagged transaction shows that vendor's historical pattern (sparkline) so the anomaly is visually obvious, not just numerically asserted.
- ⭐ **"Ask why" follow-up in assistant:** After the assistant answers, allow a one-click "why?" that re-queries the LLM with the underlying data used, showing its work.
- ⭐ **Live re-run:** A visible "Re-analyze" button that re-runs detection/forecast on demand — makes the platform feel active/live during the demo rather than static/pre-baked.

Do NOT attempt these until Phase 5 acceptance criteria for core tasks all pass.

---

## Phase 0: Setup (Target: Hour 0–1)

**T0.1** 🔴 Initialize repo structure:
```
/backend
  /routes  /services  /models  /ml
/frontend
  /src/components  /src/pages  /src/api
/data
```
**Acceptance:** `uvicorn` runs backend on a port, `npm run dev` runs frontend, both show a placeholder page/response. No errors in console.

**T0.2** 🔴 Set up `.env` and `.env.example` (LLM API key, DB path/connection string, CORS allowed origin).
**Acceptance:** App boots using values from `.env`; nothing is hardcoded; `.env` is git-ignored.

**T0.3** ⚡ Define DB schema (see Phase 1 for exact fields) and confirm migrations/table creation runs cleanly from empty DB.
**Acceptance:** Fresh DB file, run init script, tables exist with correct columns/types.

---

## Phase 1: Data Layer (Target: Hour 1–3)

**T1.1** 🔴 🎯 Design and generate the synthetic dataset. This dataset **is** the demo — invest real care here.

**Schema — `transactions`:**
| field | type | notes |
|---|---|---|
| id | int PK | |
| date | date | 6–12 months of history |
| vendor | string | 15–20 recurring vendors |
| category | string | e.g., Payroll, Utilities, SaaS, Office Supplies, Travel |
| amount | float | |
| type | enum | inflow / outflow |
| status | enum | normal / flagged / reviewed |

**Schema — `invoices`:**
| field | type | notes |
|---|---|---|
| id | int PK | |
| vendor | string | |
| amount | float | |
| invoice_date | date | |
| due_date | date | |
| status | enum | paid / pending / disputed |
| po_reference | string nullable | for 3-way match logic |

**Required injected patterns (so detection/forecasting have something real to find):**
- 15–25 anomalous transactions: unusually large amount (>5x vendor average), off-schedule timing (e.g., payroll vendor paid mid-month), round-number suspicious amounts, duplicate transactions (same vendor+amount within 3 days)
- 5–10 duplicate/near-duplicate invoices (same vendor, same amount, dates within a week)
- A clear seasonal/trend signal in aggregate cash flow (e.g., a recurring monthly dip, or a declining trend in the last 60 days) so forecasting has a real pattern to project
- At least 1 anomaly that measurably affects the cash flow trend (for the ⭐ impact-linking feature)

**Acceptance:** Generation script is re-runnable and deterministic (seeded random), produces the above counts, and a quick manual scan confirms anomalies "look" anomalous and the trend is visible if you plot raw totals.

**T1.2** 🔴 Build ingestion endpoint/script: loads seed data into DB. Idempotent — re-running doesn't duplicate rows (clear + reload, or upsert by id).
**Acceptance:** Running twice results in the same row count both times.

**T1.3** ⚡ Build read endpoints: `GET /api/transactions`, `GET /api/invoices` (with basic filtering by date range/vendor/status).
**Acceptance:** Both return correct JSON shape and support at least date-range filtering, verified with 2–3 manual requests.

🧠 **Escalation point:** If injected anomalies don't come out statistically distinguishable from normal data (e.g., z-score doesn't separate them), escalate to Claude Code with the generation script and the specific distribution parameters used.

---

## Phase 2: AI/ML Core (Target: Hour 3–8) — Critical Path

**T2.1** 🔴 🎯 Anomaly & Fraud Detection Engine

- **Method (start here):** per-vendor z-score on transaction amount + frequency-based rule (>1 transaction from same vendor within 48h flagged as "possible duplicate") + round-number heuristic (amounts ending in .00 above a threshold, optional).
- **Upgrade path (if time allows):** Isolation Forest on multi-feature vector (amount, day-of-month, vendor-category encoding, days-since-last-transaction).
- **Output contract:**
```json
{
  "transaction_id": 123,
  "risk_score": 0.87,
  "reason_code": "AMOUNT_OUTLIER" ,
  "trigger_metric": "8.2x vendor average ($450 → $3,690)",
  "vendor": "Acme SaaS Co."
}
```
- **Acceptance:** Running on seed data flags 80%+ of the deliberately injected anomalies, and flags fewer than ~5% of normal transactions as false positives. Manually verify against the injection list from T1.1.

**T2.2** 🔴 🎯 Cash Flow Forecasting Engine

- **Method:** aggregate daily/weekly net cash flow, feed to Prophet (preferred) or statsmodels ETS/ARIMA. Fallback: weighted moving average with simple trend extrapolation if library setup stalls past 45 minutes.
- **Output contract:**
```json
{
  "horizon_days": 30,
  "forecast": [{"date": "2026-10-25", "predicted_net_flow": -3200, "lower": -5100, "upper": -1400}, ...],
  "trend_summary": "Declining trend driven by increased outflows in the Payroll and SaaS categories."
}
```
- **Acceptance:** Forecast output is plausible against a manual holdout check (hide last 2 weeks of seed data, forecast, compare direction of trend — doesn't need to be numerically precise, just directionally sane).

**T2.3** 🔴 🎯 Explainability Engine — this is a judged differentiator, treat it as first-class, not a wrapper.

- **Input:** one flagged anomaly OR one forecast result, as structured JSON (never raw free text).
- **Prompt template (adapt, don't skip the structure):**
```
You are a financial analyst explaining an AI system's output to a non-technical finance manager.

Data: {structured_json_of_anomaly_or_forecast}

Rules:
- Reference at least one specific number from the data provided.
- Do not invent information not present in the data.
- Keep it to 1-3 sentences.
- Match tone to severity: risk_score > 0.85 = "highly unusual"/urgent tone; 0.6-0.85 = "worth reviewing"; below 0.6 = "minor, low priority".

Output only the explanation text, nothing else.
```
- **Validation:** After the LLM responds, check the response contains at least one digit or the vendor name from the input. If not, retry once with a stricter prompt; if it still fails, fall back to a template-based explanation (e.g., `f"This transaction is {trigger_metric} for {vendor}."`) — **never show a blank or generic explanation in the demo.**
- **Acceptance:** Every anomaly and forecast in a full test run has a non-empty, data-referencing explanation string attached.

**T2.4** ⚡ [PARALLEL] Invoice validation logic:
- Duplicate detection: same vendor + amount within a 7-day window
- Missing PO reference flag
- **Output contract:** similar shape to T2.1 (invoice_id, issue_type, detail string)
- **Acceptance:** Correctly flags all deliberately injected duplicate invoices from T1.1.

**T2.5** ⭐ Anomaly → Forecast impact linking:
- For each flagged anomaly of type outflow, recompute the forecast excluding that transaction and store the delta (`impact_on_30d_forecast`).
- **Acceptance:** At least the one deliberately-injected high-impact anomaly from T1.1 shows a visible, non-trivial delta.

🧠 **Escalation point:** If anomaly detection is wildly over/under-flagging after one calibration pass, or forecasting output is directionally wrong against the manual holdout check, escalate to Claude Code with: the model code, a sample of input data, expected vs. actual flagged/forecasted output, and what calibration was already tried.

---

## Phase 3: Backend Integration (Target: Hour 8–10)

**T3.1** 🔴 Orchestration endpoint `POST /api/analysis/run`:
- Triggers: anomaly detection → invoice validation → forecasting → explainability generation for each result → (if built) impact linking
- Persists results (or caches in memory/DB) so dashboard reads are fast, not recomputed per page load
- **Acceptance:** Single call populates everything the dashboard needs; subsequent GETs are fast (<1s).

**T3.2** 🔴 🎯 Read endpoints for frontend:
- `GET /api/anomalies` → list with risk_score, reason_code, trigger_metric, explanation
- `GET /api/forecast` → forecast array + trend_summary
- `GET /api/invoices/issues` → validation flags
- **Acceptance:** Each returns real, non-empty data after T3.1 has run once.

**T3.3** 🔴 🎯 Conversational Assistant endpoint `POST /api/assistant/query`:
- Input: `{"question": "..."}`
- Logic: classify intent loosely (keyword/heuristic is fine — e.g., contains "forecast"/"cash" → pull forecast data; "vendor"/"anomaly"/"fraud" → pull anomaly data; "invoice" → pull invoice data) → fetch that data → pass into LLM with a system prompt enforcing grounded answers only
- **System prompt must include:** "Only use the data provided below. If the answer isn't in this data, say so explicitly rather than guessing."
- **Acceptance:** Test with 5 prepared questions (see Phase 6 demo script) — every answer references real numbers from the dataset, and an out-of-scope question ("what's the weather") gets an honest "I don't have that data" response, not a hallucinated answer.

**T3.4** ✂️ Alert/status update logic: mark high-risk transactions as `needs_review` in DB when risk_score > threshold.

🧠 **Escalation point:** If the assistant's intent-routing misclassifies more than ~30% of test questions, escalate to Claude Code with the routing logic and the failing question set — this is core to the demo and worth getting right rather than patching repeatedly.

---

## Phase 4: Frontend (Target: Hour 8–14) — [PARALLEL with Phase 3 if separate sessions]

**T4.1** 🔴 🎯 Dashboard shell + KPI cards: total flagged anomalies, total flagged $ amount, 30-day forecast net position, invoice issues count. Each card should update after `/api/analysis/run`.
**Acceptance:** Cards show real numbers matching the API responses, not placeholders.

**T4.2** 🔴 🎯 Anomaly list/table: risk score (visually, e.g., color-coded badge: red >0.85, amber 0.6–0.85, gray below), vendor, amount, trigger_metric, explanation text visible inline (not hidden behind a click, for demo visibility).
**Acceptance:** All flagged anomalies from seed data render correctly with explanation text populated.

**T4.3** 🔴 🎯 Cash flow forecast chart (Recharts line chart): historical line + forecast line + shaded confidence band, trend_summary shown as a caption above/below the chart.
**Acceptance:** Chart renders with real data, confidence band visible, no NaN/undefined rendering.

**T4.4** 🔴 🎯 Conversational assistant chat UI: input box, message history, loading state while waiting for response.
**Acceptance:** Can ask a question and get a rendered, readable answer within a few seconds.

**T4.5** ⭐ Anomaly-forecast impact callout: on the anomaly detail (click-through or expand row), show "Excluding this transaction shifts the 30-day forecast by $X" using T2.5 output.

**T4.6** ⭐ Vendor sparkline: small inline chart of a vendor's transaction history when an anomaly row is expanded.

**T4.7** ✂️ Invoice validation view (table of flagged/duplicate invoices).

**T4.8** ✂️ Export button (CSV) — lowest priority, only if everything else is done and stable.

🧠 **Escalation point:** If CORS or data-shape mismatches between frontend and backend persist after 2 fix attempts, escalate to Claude Code with the exact API response payload and the frontend fetch/parsing code.

---

## Phase 5: Polish & Reliability (Target: Hour 14–20)

**T5.1** 🔴 🎯 Full end-to-end run from a clean DB: ingest → analyze → dashboard → assistant, with zero manual intervention beyond clicking "Re-analyze."
**Acceptance:** Three consecutive clean runs with no crash, no empty states, no console errors.

**T5.2** 🔴 🎯 Explainability audit: manually check every anomaly, forecast, and assistant answer shown in the current seed data — confirm each references a real number/vendor/date. This is a judged criterion — do not skip.

**T5.3** ⚡ Error handling: friendly fallback UI states for (a) LLM call failure, (b) empty data, (c) slow response (loading spinner, not a frozen screen). No raw stack traces ever shown in the UI.

**T5.4** ⚡ Visual polish pass: consistent spacing/typography, color-coding meaningful (not decorative), charts labeled and legible at demo screen-share resolution.

**T5.5** ✂️ Any remaining cut-list items from Phase 3/4, only once T5.1 and T5.2 pass.

**T5.6** 🔴 🎯 Non-hardcoding verification: add a brand-new transaction to the seed dataset (e.g., an obviously anomalous one for a vendor not previously flagged) without changing any application code, re-run ingestion + `/api/analysis/run`, and confirm the new transaction is picked up, scored, and explained correctly, and that the forecast/dashboard reflect the new data.
**Acceptance:** The newly added transaction appears as a flagged anomaly (or correctly not flagged, if it's normal) with a genuine, data-referencing explanation — with zero code changes between the two runs. This proves the pipeline computes live rather than serving fixed/cached "expected" results.

🧠 **Escalation point:** If the app breaks intermittently (not consistently reproducible within 15 minutes), escalate to Claude Code with exact repro steps tried, logs, and what varies between successful/failed runs. Do not keep patching blindly this close to the demo.

---

## Phase 6: Demo Rehearsal (Target: Hour 20–24)

**T6.1** 🔴 🎯 Prepare and rehearse exact assistant questions to ask live (have these pre-tested, not improvised):
1. "What's our cash flow forecast for the next 30 days?"
2. "Which vendors have unusual transaction activity?"
3. "Are there any duplicate invoices I should know about?"
4. "Why is [specific flagged vendor] marked as high risk?"
5. (out-of-scope control question) "What's the stock market doing today?" — to demonstrate honest "I don't know" behavior

**T6.2** 🔴 🎯 Full dry-run matching the Section 0 demo narrative beats, timed to ~3 minutes. Practice the anomaly → forecast impact moment specifically — it's the differentiator, don't fumble it.

**T6.3** 🔴 🎯 Freeze code after dry-run passes twice cleanly. Only critical bug fixes allowed after this point.

**T6.4** ⚡ Record a backup video of a full successful run, in case of live demo/network/API failure.

**T6.5** ⚡ Prepare a one-line answer for likely judge questions: "How do you prevent hallucination in the assistant?" (answer: grounded prompting + data-only system instructions + explicit fallback), "How does this scale beyond synthetic data?" (answer: same pipeline works against any transactional DB export/API).

---

## Cut List (in strict priority order if time runs out)

1. Export/reports (CSV/PDF)
2. Vendor sparkline (⭐ T4.6)
3. Invoice validation UI (keep backend logic if built, skip the view)
4. Alert status updates (T3.4)
5. Anomaly→forecast impact linking (⭐ T2.5/T4.5) — cut last among the ⭐ items, it's the biggest differentiator

**Never cut, under any circumstance:** anomaly detection, forecasting, explainability text on every output, dashboard core view, conversational assistant. These are the entire demo narrative — everything else is amplification.

---

## Judging Criteria → Task Mapping

| Judging Signal | Tasks That Deliver It |
|---|---|
| Data-driven reasoning | T1.1, T2.1, T2.2 |
| Anomaly detection | T2.1, T4.2 |
| Forecasting | T2.2, T4.3 |
| Explainability | T2.3, T5.2, T4.2, T4.4 |
| Intelligent automation | T2.4, T3.1, T3.4 |
| Overall demo polish/reliability | T5.1, T5.3, T6.1–T6.4 |
| "Wow" differentiation | T2.5, T4.5, T1.1 (impact-linked anomaly) |
