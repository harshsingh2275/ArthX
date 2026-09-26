"""
ArthX Conversational Assistant Engine — T3.3
==============================================
Pure LLM interaction layer for answering natural language financial questions.
Enforces grounded answers based strictly on internal system data.

Mandatory System Prompt Rule (TASK.md T3.3):
  "Only use the data provided below. If the answer isn't in this data, say so explicitly rather than guessing."
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from config import settings

logger = logging.getLogger(__name__)

ASSISTANT_SYSTEM_PROMPT = """\
You are ArthX Assistant, an AI financial intelligence copilot for finance managers.

Only use the data provided below. If the answer isn't in this data, say so explicitly rather than guessing.

Rules:
1. Grounding: When answering questions about the company's finances, you must cite specific numbers, dollar amounts, vendor names, dates, or percentages directly from the provided data.
2. Conciseness: Keep answers concise, clear, and direct (2 to 4 sentences or a tight bulleted list). Do not ramble.
3. Out-of-scope queries: If the question is outside the scope of the provided data (e.g. general world knowledge, stock markets, weather, competitors), explicitly state that you do not have access to that information and clarify that you only cover ArthX's transactions, anomalies, cash flow forecasts, and invoice validation.
4. Accuracy: Never hallucinate or extrapolate numbers not present in the data context.\
"""

USER_PROMPT_TEMPLATE = """\
User Question: {question}

Data Context:
{context_json}

Provide a direct, grounded answer according to your system instructions:\
"""


def _call_groq_assistant(prompt: str) -> Optional[str]:
    """Execute Groq chat completion for assistant query."""
    try:
        from groq import Groq

        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": ASSISTANT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,   # low temperature for strict factual adherence
            max_tokens=350,
        )
        text = completion.choices[0].message.content
        return text.strip() if text else None
    except Exception as exc:
        logger.warning("Groq Assistant API call failed: %s", exc)
        return None


def _deterministic_fallback_answer(question: str, intent: str, context: Dict[str, Any]) -> str:
    """Deterministic fallback if LLM service is offline."""
    if intent == "OUT_OF_SCOPE":
        return (
            "I don't have that data. I only have access to ArthX's internal financial records, "
            "including transactions, anomaly detection, cash flow forecasts, and invoice validation."
        )

    if intent == "FORECAST":
        summary = context.get("trend_summary", "")
        horizon = context.get("horizon_days", 30)
        total_30d = context.get("projected_30d_net_flow")
        total_str = f" projecting a total 30-day net flow of ${total_30d:,.2f}" if total_30d is not None else ""
        return f"For the next {horizon} days, our cash flow forecast{total_str} shows: {summary}"

    if intent in ("ANOMALIES", "VENDOR_ANOMALY"):
        vendor = context.get("target_vendor")
        if vendor and context.get("vendor_anomalies"):
            anoms = context["vendor_anomalies"]
            details = [f"TxID {a.get('transaction_id')} (${a.get('amount', 0):,.2f}, risk {a.get('risk_score')}: {a.get('trigger_metric')})" for a in anoms]
            return f"{vendor} is flagged due to unusual activity: {'; '.join(details)}."
        flagged = context.get("flagged_anomalies", [])
        if flagged:
            top_vendors = [f"{a.get('vendor')} (${a.get('amount', 0):,.2f}, risk {a.get('risk_score')})" for a in flagged[:4]]
            return f"The following vendors have unusual transaction activity: {', '.join(top_vendors)}."
        return "No high-risk anomalous transaction activity was detected."

    if intent == "INVOICES":
        dups = context.get("duplicate_invoices", [])
        missing_po = context.get("missing_po_count", 0)
        dup_count = len(dups)
        sample = [f"{d.get('vendor')} (${d.get('amount', 0):,.2f})" for d in dups[:3]]
        sample_str = f" including {', '.join(sample)}" if sample else ""
        return (
            f"There are {dup_count} duplicate invoices detected within 7-day windows{sample_str}, "
            f"and {missing_po} invoices missing purchase order (PO) references."
        )

    return "I do not have sufficient data in the system to answer this question."


def generate_assistant_response(
    question: str,
    intent: str,
    context_data: Dict[str, Any],
) -> str:
    """
    Generate grounded assistant answer using Groq with deterministic fallback.
    """
    if not settings.has_llm_key or settings.EXPLAINABILITY_MODE == "template":
        return _deterministic_fallback_answer(question, intent, context_data)

    context_json = json.dumps(context_data, indent=2, default=str)
    prompt = USER_PROMPT_TEMPLATE.format(question=question, context_json=context_json)

    answer = _call_groq_assistant(prompt)
    if answer:
        return answer

    return _deterministic_fallback_answer(question, intent, context_data)
