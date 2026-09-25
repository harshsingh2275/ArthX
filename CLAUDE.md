# CLAUDE.md — ArthX (CTRL ALT HACK)
### Source of truth for AI coding agents (Google Antigravity primary, Claude Code for escalation only)

---

## 1. Project Summary

ArthX is an explainable AI financial intelligence platform. For the hackathon MVP, it does **one coherent end-to-end job**:

> Ingest financial data (transactions + invoices) → detect anomalies/fraud → forecast cash flow → explain every AI output in plain language → surface it all in a dashboard + a conversational assistant.

Do not expand scope beyond what's in this file and TASK.md. If a feature isn't in TASK.md, don't build it without flagging the ambiguity first.

---

## 2. MVP Scope Decisions (final — do not silently change)

To keep this buildable in 24 hours, the following simplifications are **intentional architecture decisions**, not oversights:

| Original Idea | Hackathon MVP Decision | Reason |
|---|---|---|
| OCR on scanned PDF invoices | Invoices ingested as structured CSV/JSON (simulating extracted data) | OCR adds fragile complexity with low demo payoff |
| PostgreSQL + Redis | SQLite (or single Postgres instance) only, no Redis | One datastore is enough at hackathon data volume |
| Real email/Slack/webhook alerts | In-app visual alert badges only | External integrations are demo risk, not core value |
| Full ERP API layer | Skip unless all core tasks are done early | Nice-to-have, not core workflow |
| PDF/CSV/Excel export | Skip unless all core tasks are done early | Nice-to-have, not core workflow |
| Budget Optimization Engine | Cut from MVP; mention only in pitch as roadmap | Core value is anomaly detection + forecasting + explainability |

**Core MVP features (must work end-to-end):**
1. Data ingestion (seeded synthetic dataset)
2. Anomaly/fraud detection on transactions
3. Cash flow forecasting
4. Explainability layer (LLM-generated rationale grounded in real data)
5. Dashboard (risk flags + forecast chart + KPIs)
6. Conversational assistant (answers grounded in computed data only)

---

## 3. Architecture

```
Synthetic/Seed Data (CSV/JSON)
        │
        ▼
Data Ingestion Service (backend) ──▶ SQLite/Postgres
        │
        ▼
AI/ML Core (backend services, called synchronously or via simple job runner):
   ├─ Anomaly & Fraud Detection Engine (scikit-learn / statistical rules)
   ├─ Cash Flow Forecasting Engine (Prophet / statsmodels / simple moving-avg fallback)
   └─ Explainability Engine (LLM call, grounded in the specific flagged rows/stats — never free-floating)
        │
        ▼
Backend API (FastAPI)
        │
        ▼
┌───────────────┬─────────────────────┐
│ React Dashboard│ Conversational Assistant (chat → backend → grounded LLM answer) │
└───────────────┴─────────────────────┘
```

**Grounding rule (non-negotiable):** Every LLM call for explanation or Q&A must receive the actual relevant data (rows, aggregates, stats) in its prompt context. Never let the LLM answer from general knowledge about "typical" finance patterns — it must cite specific numbers/records from this dataset.

---

## 4. Tech Stack

- **Frontend:** React + Tailwind CSS, Recharts for charts
- **Backend:** Python + FastAPI
- **Database:** SQLite for hackathon speed (swap to Postgres only if already comfortable — don't spend time migrating mid-hackathon)
- **ML:** scikit-learn / PyOD (anomaly detection), Prophet or statsmodels (forecasting) — fallback to simple statistical methods (z-score, moving average) if libraries cause friction
- **LLM:** Claude or Gemini API (via Antigravity's built-in models) for explanation generation and the conversational assistant
- **Auth:** Skip unless explicitly tasked — hackathon demo runs single-user, no login flow unless time allows

---

## 5. Repository Conventions

- Backend: `/backend` — FastAPI app, organized as `routes/`, `services/`, `models/`, `ml/`
- Frontend: `/frontend` — React app, organized as `components/`, `pages/`, `api/`
- Data: `/data` — seed CSV/JSON files, data generation scripts
- One service = one responsibility (e.g., `ml/anomaly_detector.py` does anomaly detection only, doesn't also format API responses)
- Environment variables in `.env` (never committed); use `.env.example` as template
- **Never hardcode API keys or secrets** — always read from environment variables

---

## 6. Coding & Agent Behavior Rules

- **Inspect existing code before modifying.** Never rewrite a working file from scratch to add one feature.
- Follow TASK.md in order. Do not skip ahead unless a task is explicitly marked parallelizable.
- Keep functions small and single-purpose. No premature abstraction — hackathon code should be readable, not "enterprise architected."
- Do not introduce a new library/framework not listed in Section 4 without flagging it first.
- When a requirement is ambiguous, choose the simplest solution that keeps the end-to-end demo working, and note the assumption in a code comment.
- Preserve previously working functionality — if a change breaks an earlier working feature, fix it before moving to the next task.
- Fix root causes, not symptoms (e.g., don't silence an error, understand why it happens).
- **No hardcoded outputs, ever.** Anomaly scores, forecast values, risk flags, and explanations must be computed at runtime by the actual model/logic against whatever data is currently in the database — never a fixed list of "expected" anomaly IDs, a pre-written forecast array, or a canned explanation string mapped to a specific transaction. If a shortcut like this is taken to "make the demo work faster," it must be flagged to the user immediately, not shipped silently. The only acceptable fallback is the template-based explanation in Section 7, and only after a real LLM call has been attempted and failed validation — never as the default path.

---

## 7. Explainability Requirements (applies to every AI output)

Every anomaly flag, forecast, or assistant answer must include:
1. **What** was flagged/predicted/answered
2. **Why** — the specific data points or statistical reasoning behind it (e.g., "this transaction is 8x the vendor's average" not "this looks unusual")
3. Confidence/severity indicator where applicable

If an LLM-generated explanation doesn't reference concrete numbers from the dataset, treat it as a bug and fix the prompt.

---

## 8. Testing Expectations

- Test the full ingestion → detection → forecast → dashboard pipeline end-to-end after each major task, not just unit-level
- Verify frontend changes by actually running the app and checking the browser, not just reading code
- For ML components: sanity-check outputs against the seed dataset manually (does the flagged anomaly actually look anomalous?)
- No formal test suite required given time constraints — manual verification is acceptable, but must happen after every meaningful change

---

## 9. Security Rules (minimum bar for hackathon)

- No secrets/API keys in code or committed files
- Sanitize any user input that reaches the LLM prompt or DB query (basic injection hygiene)
- CORS configured narrowly (frontend origin only), not wide open in a way that's copy-pasted into production later
- No PII/real financial data — synthetic data only

---

## 10. When to Escalate to Claude Code

Escalate — don't keep retrying in Antigravity — when:
- An error repeats after 2 fix attempts in Antigravity
- A decision affects the core architecture (e.g., changing the DB, restructuring the ML pipeline)
- A security concern is found (e.g., prompt injection risk in the assistant, data leakage)
- Forecasting or anomaly detection outputs look statistically wrong and the cause isn't obvious
- Antigravity proposes a fix that would silently change scope or rewrite significant working code

**When escalating, provide:** the exact file(s), the error/symptom, what was already tried, and the specific question to answer (see TASK.md escalation markers for pre-flagged points).

---

## 11. Priority Order (when time runs out)

1. Working end-to-end MVP (ingestion → detection → forecast → dashboard)
2. Demo reliability (no crashes, seeded data always works)
3. Data-grounded outputs (no hallucinated numbers)
4. Explainability (visible rationale on every flag/forecast)
5. Core UX polish (clean dashboard, working chat)
6. Security/error handling
7. UI polish
8. Nice-to-haves (exports, API layer, alerts integrations)

Refer to TASK.md for the exact execution sequence and cut list.
