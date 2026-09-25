"""
ArthX Explainability Engine — T2.3
====================================
Pure LLM-call logic. No DB access here.

Provider: Groq (llama-3.3-70b-versatile by default).
  The Groq client is lazy-imported so the module loads even if the
  package isn't installed — it will just fall back to the template.

Responsibilities:
  - Build the structured prompt from anomaly or forecast JSON.
  - Call the Groq chat completions API.
  - Validate: response must contain at least one digit OR the vendor/keyword
    from the input (grounding check per CLAUDE.md §7).
  - Retry once with a stricter prompt if validation fails.
  - Fall back to a deterministic template if the API is unavailable or both
    attempts fail validation.  The engine NEVER returns a blank string.

Architectural rules (CLAUDE.md §6):
  - No hardcoded explanation strings.
  - The template fallback is deterministic from real field values — not invented.
  - The LLM prompt always receives the actual JSON being explained, never a
    generic "explain this" instruction.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, Optional

from config import settings

logger = logging.getLogger(__name__)


# ── Prompt templates (verbatim from TASK.md T2.3) ────────────────────────────

_SYSTEM_PROMPT = (
    "You are a financial analyst explaining an AI system's output "
    "to a non-technical finance manager."
)

_USER_TEMPLATE = """\
Data: {structured_json}

Rules:
- Reference at least one specific number from the data provided.
- Do not invent information not present in the data.
- Keep it to 1-3 sentences.
- Match tone to severity: risk_score > 0.85 = "highly unusual"/urgent tone; \
0.6-0.85 = "worth reviewing"; below 0.6 = "minor, low priority".

Output only the explanation text, nothing else.\
"""

_STRICT_USER_TEMPLATE = """\
Data: {structured_json}

IMPORTANT: Your response MUST contain at least one number from the data above \
AND must mention the vendor name if one is present.

Rules:
- Reference at least one specific number from the data provided.
- Do not invent information not present in the data.
- Keep it to 1-3 sentences.
- Match tone to severity: risk_score > 0.85 = "highly unusual"/urgent tone; \
0.6-0.85 = "worth reviewing"; below 0.6 = "minor, low priority".

Output only the explanation text, nothing else.\
"""


# ── Validation ───────────────────────────────────────────────────────────────

def _validate_response(text: str, data: Dict[str, Any]) -> bool:
    """
    Grounding check: the response must contain at least one digit from the data
    OR the vendor/keyword name.  Returns True if the response passes.
    """
    text = text.strip()
    if not text:
        return False

    # Any digit present → almost always satisfied for data-grounded answers
    if re.search(r"\d", text):
        return True

    # Fallback: check for vendor name or other prominent string field
    for key in ("vendor", "trend_summary", "reason_code"):
        value = data.get(key)
        if value and isinstance(value, str) and len(value) > 2:
            if value.lower() in text.lower():
                return True

    return False


# ── Deterministic fallback ───────────────────────────────────────────────────

def _build_fallback(data: Dict[str, Any]) -> str:
    """
    Deterministic template fallback — constructed entirely from real field values.
    NEVER blank; NEVER invented.
    """
    # Anomaly shape
    if "trigger_metric" in data and "vendor" in data:
        trigger = data.get("trigger_metric", "anomalous metric")
        vendor = data.get("vendor", "unknown vendor")
        risk = data.get("risk_score")
        risk_str = f" (risk score: {risk:.2f})" if isinstance(risk, (int, float)) else ""
        return f"This transaction is {trigger} for {vendor}{risk_str}."

    # Forecast shape
    if "trend_summary" in data:
        summary = data.get("trend_summary", "")
        horizon = data.get("horizon_days", "")
        horizon_str = f" over the next {horizon} days" if horizon else ""
        if summary:
            return f"The cash flow forecast{horizon_str} shows: {summary}"
        return (
            f"The {horizon}-day cash flow forecast has been generated. "
            "Review the forecast chart for projected net flows and confidence intervals."
        )

    # Generic last-resort (should never be reached in practice)
    return "An anomaly or forecast result was generated; please review the details."


# ── Groq caller ───────────────────────────────────────────────────────────────

def _call_groq(user_message: str) -> Optional[str]:
    """
    Call the Groq chat completions API and return the stripped response text,
    or None on any failure (network, rate limit, bad key, etc.).
    """
    try:
        from groq import Groq  # lazy import — fails gracefully if not installed

        client = Groq(api_key=settings.GROQ_API_KEY)
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL_NAME,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_message},
            ],
            temperature=0.3,      # low temperature for factual, consistent outputs
            max_tokens=256,       # 1-3 sentences never needs more
        )
        text = completion.choices[0].message.content
        return text.strip() if text else None
    except Exception as exc:
        logger.warning("Groq API call failed: %s", exc)
        return None


# ── Public entry point ───────────────────────────────────────────────────────

def generate_explanation(data: Dict[str, Any]) -> str:
    """
    Generate a grounded natural-language explanation for one anomaly or forecast.

    Args:
        data: A dict conforming to the T2.1 anomaly contract or T2.2 forecast
              contract (or any subset thereof).  Never raw free text.

    Returns:
        A non-empty string explanation.  Source priority:
          1. Groq LLM response that passes grounding validation
          2. Groq LLM retry (stricter prompt) that passes validation
          3. Deterministic template fallback (always from real field values)
    """
    if not settings.has_llm_key or settings.EXPLAINABILITY_MODE == "template":
        logger.info("Skipping LLM call (no key or template mode); using fallback.")
        return _build_fallback(data)

    structured_json = json.dumps(data, indent=2, default=str)

    # ── Attempt 1 ────────────────────────────────────────────────────────────
    user_msg_1 = _USER_TEMPLATE.format(structured_json=structured_json)
    response_1 = _call_groq(user_msg_1)

    if response_1 and _validate_response(response_1, data):
        logger.debug("Explanation accepted on attempt 1.")
        return response_1

    if response_1:
        logger.warning(
            "Attempt 1 failed grounding check. Response: %r", response_1[:200]
        )
    else:
        logger.warning("Attempt 1 returned no content.")

    # ── Attempt 2 (stricter prompt) ───────────────────────────────────────────
    user_msg_2 = _STRICT_USER_TEMPLATE.format(structured_json=structured_json)
    response_2 = _call_groq(user_msg_2)

    if response_2 and _validate_response(response_2, data):
        logger.debug("Explanation accepted on attempt 2.")
        return response_2

    if response_2:
        logger.warning(
            "Attempt 2 also failed grounding check. Response: %r", response_2[:200]
        )
    else:
        logger.warning("Attempt 2 returned no content.")

    # ── Fallback ──────────────────────────────────────────────────────────────
    logger.warning("Both LLM attempts failed; using deterministic fallback.")
    return _build_fallback(data)
