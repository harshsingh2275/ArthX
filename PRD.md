# Product Requirements Document (PRD) — ArthX

**Project:** ArthX — AI-Powered Financial Intelligence Platform
**Track:** CTRL ALT HACK, Track 3: Finance
**Format:** 24-hour hackathon MVP
**Status:** Planning complete, implementation not yet started

---

## 1. Purpose

ArthX is an explainable AI platform that automates financial operations analysis — detecting anomalies, forecasting cash flow, and answering business questions — while showing its reasoning for every output. It targets the core gap identified in Track 3: existing finance tools either automate data entry without reasoning, or provide AI insights without explanation. ArthX does both together.

Full problem-space analysis: see `finance-track-analysis.md`.

---

## 2. Goals

**Primary goal:** Ship a working, demoable end-to-end pipeline — ingest data → detect anomalies → forecast cash flow → explain every output → surface it in a dashboard and a conversational assistant — within 24 hours.

**Secondary goals (only after primary goal is solid):**
- Demonstrate cross-feature reasoning (an anomaly's measurable impact on the forecast), not just isolated model outputs
- Present a polished, judge-ready live demo with no crashes

**Non-goals for this MVP:** production-grade security, multi-tenant support, real accounting/ERP integration, handling real (non-synthetic) financial data, mobile responsiveness.

---

## 3. Target Users

| Persona | Need |
|---|---|
| Finance Manager / Controller | Wants flagged anomalies and invoice issues surfaced automatically, with clear reasons, instead of manual line-by-line review |
| CFO / Business Owner | Wants fast, plain-language answers to financial questions and forward visibility into cash position |
| Accounts Payable Team | Wants duplicate invoices and vendor risk flagged before payment is issued |

(For the hackathon demo, these personas inform UX copy and the assistant's Q&A design — there is no multi-user login system in the MVP.)

---

## 4. User Stories

1. As a finance manager, I want to see which transactions are flagged as unusual **and why**, so I can decide whether to investigate without re-deriving the reasoning myself.
2. As a CFO, I want to see a 30/60/90-day cash flow forecast with a plain-language trend summary, so I can plan spending decisions.
3. As a CFO, I want to ask a question in plain English ("What's our forecast for next month?") and get an answer grounded in real numbers, not a generic response.
4. As an AP team member, I want duplicate or suspicious invoices flagged automatically, so I don't pay the same vendor twice.
5. As a judge/demo viewer, I want to see that a specific flagged anomaly directly affects the forecast, so it's clear the system reasons across data, not just per-feature in isolation.
6. As any user, I want the assistant to admit when it doesn't have the data to answer, rather than guessing — so I can trust what it does answer.

---

## 5. Functional Requirements

### 5.1 Data Ingestion
- FR1: System shall ingest a synthetic dataset of transactions and invoices from CSV/JSON into a database.
- FR2: Ingestion shall be idempotent — re-running does not duplicate records.
- FR3: Seed data shall include deliberately injected anomalies and duplicate invoices (see `TASK.md` T1.1 for exact spec) so detection has real signal to find.

### 5.2 Anomaly & Fraud Detection
- FR4: System shall score each transaction with a risk score (0–1) using per-vendor statistical deviation and frequency-based rules.
- FR5: Each flagged transaction shall include a specific trigger metric (e.g., "8.2x vendor average") — not just a raw score.
- FR6: Detection shall correctly flag at least 80% of deliberately injected anomalies in the seed dataset, with a false-positive rate under ~5% on normal transactions.

### 5.3 Cash Flow Forecasting
- FR7: System shall forecast net cash flow for a configurable horizon (default 30 days) with a confidence range.
- FR8: Forecast output shall include a plain-language trend summary (e.g., which category is driving the trend).
- FR9: Forecast direction shall be validated against a manual holdout check before being trusted for demo.

### 5.4 Explainability Layer
- FR10: Every anomaly flag, forecast, and assistant answer shall include an explanation that references at least one specific number or entity from the underlying data.
- FR11: Explanation tone shall scale with severity/confidence (e.g., high risk score → urgent language, low score → "worth a look").
- FR12: If an LLM-generated explanation fails to reference concrete data, the system shall fall back to a template-based explanation rather than showing a blank or generic one.

### 5.5 Invoice Validation
- FR13: System shall detect duplicate/near-duplicate invoices (same vendor + amount within a 7-day window).
- FR14: System shall flag invoices missing a PO reference.

### 5.6 Conversational Assistant
- FR15: System shall accept natural-language questions and route them to the relevant precomputed data (anomalies, forecast, or invoices) based on intent.
- FR16: Answers shall be grounded strictly in retrieved data; the system prompt shall instruct the model to say "I don't have that data" rather than hallucinate when a question falls outside available data.
- FR17: The assistant shall correctly handle at least 5 prepared demo questions, including one deliberately out-of-scope control question.

### 5.7 Dashboard
- FR18: Dashboard shall display KPI cards (total flagged anomalies, flagged $ amount, 30-day forecast net position, invoice issue count).
- FR19: Dashboard shall display an anomaly list with risk-score-based visual indicators (color-coded).
- FR20: Dashboard shall display a cash flow chart with historical and forecasted values plus a confidence band.

### 5.8 Standout Feature (Differentiator)
- FR21 (⭐): System shall compute and display, for at least one flagged anomaly, how excluding it changes the cash flow forecast (impact-linking).

---

## 6. Non-Functional Requirements

- **NFR1 — Grounding:** No AI output (explanation, forecast narrative, or assistant answer) may present information not traceable to the actual dataset. This is treated as a correctness bug, not a style issue.
- **NFR2 — Reliability:** The full pipeline (ingest → analyze → dashboard → assistant) must complete a clean run with zero crashes across at least 3 consecutive tries before the demo.
- **NFR3 — Security (hackathon-appropriate minimum):** No hardcoded secrets/API keys; basic input sanitization on data reaching the LLM prompt or DB query; narrow CORS configuration; synthetic data only, no real PII/financial data.
- **NFR4 — Simplicity:** No technology or dependency introduced beyond what's listed in `CLAUDE.md` Section 4 without explicit justification.
- **NFR5 — Performance:** Dashboard reads should return in under ~1 second after initial analysis has run (results cached/persisted, not recomputed per page load).

---

## 7. Out of Scope (explicit, to prevent scope creep)

- OCR / scanned PDF invoice extraction (structured CSV/JSON used instead)
- Redis or any secondary caching layer
- Real email/Slack/webhook alert integrations (in-app badges only)
- ERP/accounting system API integration layer
- CSV/PDF/Excel export functionality (only if all core tasks finish early)
- Dynamic Budget Optimization Engine (mentioned only in the pitch as a roadmap item)
- User authentication / multi-user support
- Mobile-responsive design

---

## 8. Success Metrics (Hackathon Context)

| Metric | Target |
|---|---|
| End-to-end pipeline works live | Yes/No — must be Yes |
| Anomaly detection accuracy on seed data | ≥80% of injected anomalies flagged, ≤5% false positive rate |
| Every displayed AI output has a grounded explanation | 100% |
| Assistant answers correctly on prepared demo questions | 5/5, including correct refusal on out-of-scope question |
| Demo runs without crash across rehearsals | 3/3 clean runs |
| Judging criteria alignment | See mapping table in `TASK.md` Section "Judging Criteria → Task Mapping" |

---

## 9. Assumptions & Constraints

- Built in a 24-hour hackathon window; primary implementation happens in Google Antigravity using its built-in Gemini/Claude models.
- Claude Code is used only for escalation (architecture decisions, hard bugs, security review) — not primary development.
- Data is synthetic/seeded, not real financial data, due to time and privacy constraints.
- Single-user, single-session demo context — no concurrency or multi-tenant requirements.

---

## 10. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM explanation hallucinates numbers | Validate response contains real data references; fall back to template explanation if not |
| Anomaly detection over/under-flags | Calibrate against injected anomaly list in seed data before moving on; escalate to Claude Code if miscalibrated after one pass |
| Forecasting model setup consumes too much time | Fallback to weighted moving average if Prophet/statsmodels setup exceeds 45 minutes |
| Demo breaks live | Full dry-run rehearsal (2x clean passes) + backup recorded video as fallback |
| Scope creep from the 8 possible track directions | This PRD's Section 7 (Out of Scope) is final unless explicitly revisited |

---

## 11. Release Plan

Mapped directly to `TASK.md` phases:

| Phase | Hour Target | Deliverable |
|---|---|---|
| 0 — Setup | 0–1 | Repo skeleton, env config, DB schema |
| 1 — Data Layer | 1–3 | Seed dataset, ingestion, read endpoints |
| 2 — AI/ML Core | 3–8 | Anomaly detection, forecasting, explainability, invoice validation |
| 3 — Backend Integration | 8–10 | Orchestration endpoint, assistant endpoint |
| 4 — Frontend | 8–14 (parallel) | Dashboard, charts, chat UI |
| 5 — Polish & Reliability | 14–20 | End-to-end testing, error handling, explainability audit |
| 6 — Demo Rehearsal | 20–24 | Scripted demo, code freeze, backup recording |

---

## 12. Reference Documents

- `finance-track-analysis.md` — problem space, gaps, evaluation criteria
- `CLAUDE.md` — architecture, tech stack, coding/security/testing rules
- `TASK.md` — granular execution roadmap with acceptance criteria
- `AGENTS.md` — Antigravity auto-load entry point
- `PROJECT-CONTEXT-SUMMARY.md` — condensed context for external AI tools
