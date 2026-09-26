"""
ArthX Assistant Service — T3.3
================================
Handles natural language intent routing and context data aggregation:
  1. Identifies query intent: FORECAST, ANOMALIES, VENDOR_ANOMALY, INVOICES, SUMMARY, OUT_OF_SCOPE
  2. Fetches grounded real-time data from database tables
  3. Sends grounded context to the assistant LLM
  4. Returns structured query response
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from models.anomaly import Anomaly
from models.transaction import Transaction
from models.invoice_issue import InvoiceIssue
from models.forecast import Forecast
from services.analysis import get_stored_anomalies, FLAG_THRESHOLD
from services.forecast import get_stored_forecast
from services.invoice_validation import get_stored_invoice_issues
from ml.assistant import generate_assistant_response


# ── Vendor Recognition ───────────────────────────────────────────────────────

KNOWN_VENDORS = [
    "PowerGrid Utilities",
    "DataSync SaaS",
    "CloudOps Pro",
    "LegalEdge Partners",
    "OfficeDepot Supplies",
    "Broadband Express",
    "ArunCapital Payroll",
    "ClientFirst Revenue",
    "FlightEasy Travel",
    "MaintenancePro",
    "TechGear Solutions",
    "SecureVault AI",
    "AquaFlow Services",
    "AdNova Marketing",
    "ContractPlus Ltd",
    "RetainerB2B Inc",
    "ProjectAlpha Revenue",
    "HotelStay Corp",
]


def _detect_vendor_in_question(q: str) -> Optional[str]:
    """Check if any known vendor name or prefix is mentioned in the query."""
    q_lower = q.lower()
    for vendor in KNOWN_VENDORS:
        # Check full name or primary identifying word
        vendor_lower = vendor.lower()
        if vendor_lower in q_lower:
            return vendor
        # Check first token for distinct vendors (e.g. "PowerGrid", "DataSync", "CloudOps")
        first_token = vendor_lower.split()[0]
        if len(first_token) >= 5 and first_token in q_lower:
            return vendor
    return None


# ── Intent Classification ───────────────────────────────────────────────────

def classify_intent(question: str) -> Tuple[str, Optional[str]]:
    """
    Classify intent using heuristic keyword and entity matching.
    Returns (intent, target_entity).
    """
    q = question.lower().strip()

    # 1. Out-of-scope check (external market, world events, general topics)
    out_of_scope_patterns = [
        r"\bstock\b", r"\bmarket\b", r"\bdow\b", r"\bnasdaq\b", r"\bs&p\b",
        r"\bweather\b", r"\bcrypto\b", r"\bbitcoin\b", r"\belection\b",
        r"\bpresident\b", r"\bsports\b", r"\bgame\b", r"\bscore\b",
        r"\bwho is\b", r"\bcapital of\b", r"\bmacroeconomic\b",
    ]
    for pattern in out_of_scope_patterns:
        if re.search(pattern, q):
            return "OUT_OF_SCOPE", None

    # 2. Specific vendor inquiry
    matched_vendor = _detect_vendor_in_question(question)
    if matched_vendor:
        return "VENDOR_ANOMALY", matched_vendor

    # 3. Forecast queries
    forecast_kws = [
        "forecast", "cash flow", "cashflow", "next 30", "horizon",
        "runway", "project", "projection", "liquidity", "future net",
        "predict", "burn rate",
    ]
    if any(kw in q for kw in forecast_kws):
        return "FORECAST", None

    # 4. Anomaly / Fraud / Risk queries
    anomaly_kws = [
        "unusual", "anomal", "suspicious", "fraud", "risk",
        "flag", "flagged", "outlier", "spike", "activity", "irregular",
    ]
    if any(kw in q for kw in anomaly_kws):
        return "ANOMALIES", None

    # 5. Invoices / PO queries
    invoice_kws = [
        "invoice", "invoices", "po", "purchase order", "duplicate",
        "bill", "billing", "3-way", "match", "unmatched",
    ]
    if any(kw in q for kw in invoice_kws):
        return "INVOICES", None

    # 6. Overall summary
    summary_kws = ["summary", "overview", "health", "status", "dashboard", "how are we doing"]
    if any(kw in q for kw in summary_kws):
        return "SUMMARY", None

    # Fallback to out-of-scope if completely unrecognized
    return "OUT_OF_SCOPE", None


# ── Context Data Fetching ────────────────────────────────────────────────────

def fetch_grounded_context(
    db: Session,
    intent: str,
    target_vendor: Optional[str] = None,
) -> Tuple[Dict[str, Any], List[str]]:
    """
    Fetch exact ground-truth records matching the identified intent.
    Returns (context_dict, data_source_names).
    """
    context: Dict[str, Any] = {}
    data_sources: List[str] = []

    if intent == "FORECAST":
        fc = get_stored_forecast(db)
        points = fc.get("forecast", [])
        if points:
            flows = [p["predicted_net_flow"] for p in points]
            total_30d = round(sum(flows), 2)
            context["horizon_days"] = fc.get("horizon_days", 30)
            context["projected_30d_net_flow"] = total_30d
            context["trend_summary"] = fc.get("trend_summary", "")
            context["daily_predicted_range"] = {
                "min_daily_net_flow": min(flows),
                "max_daily_net_flow": max(flows),
                "start_date": points[0]["date"],
                "end_date": points[-1]["date"],
            }
        else:
            context["forecast"] = "No forecast computed yet."
        data_sources.append("forecasts")

    elif intent == "VENDOR_ANOMALY":
        vendor_name = target_vendor or "Unknown"
        anomalies = (
            db.query(Anomaly)
            .filter(Anomaly.vendor.ilike(f"%{vendor_name}%"))
            .all()
        )
        recent_txs = (
            db.query(Transaction)
            .filter(Transaction.vendor.ilike(f"%{vendor_name}%"))
            .order_by(Transaction.date.desc())
            .limit(5)
            .all()
        )
        context["target_vendor"] = vendor_name
        context["vendor_anomalies"] = [a.to_dict() for a in anomalies]
        context["recent_transactions"] = [t.to_dict() for t in recent_txs]
        data_sources.extend(["anomalies", "transactions"])

    elif intent == "ANOMALIES":
        anomalies = get_stored_anomalies(db, min_risk=FLAG_THRESHOLD)
        context["flagged_count"] = len(anomalies)
        context["flagged_anomalies"] = [
            {
                "transaction_id": a["transaction_id"],
                "vendor": a["vendor"],
                "amount": a["amount"],
                "risk_score": a["risk_score"],
                "reason_code": a["reason_code"],
                "trigger_metric": a["trigger_metric"],
                "explanation": a["explanation"],
                "impact_on_30d_forecast": a.get("impact_on_30d_forecast"),
            }
            for a in anomalies[:10]  # top 10 highest risk
        ]
        data_sources.append("anomalies")

    elif intent == "INVOICES":
        issues = get_stored_invoice_issues(db)
        dups = [i for i in issues if i["issue_type"] == "DUPLICATE_INVOICE"]
        missing_po = [i for i in issues if i["issue_type"] in ("MISSING_PO_REFERENCE", "MISSING_PO")]
        context["total_invoice_issues"] = len(issues)
        context["duplicate_invoices_count"] = len(dups)
        context["missing_po_count"] = len(missing_po)
        context["duplicate_invoices"] = dups
        context["missing_po_sample"] = missing_po[:5]
        data_sources.append("invoice_issues")

    elif intent == "SUMMARY":
        fc = get_stored_forecast(db)
        anomalies = get_stored_anomalies(db, min_risk=FLAG_THRESHOLD)
        issues = get_stored_invoice_issues(db)
        context["forecast_trend"] = fc.get("trend_summary", "")
        context["flagged_anomalies_count"] = len(anomalies)
        context["invoice_issues_count"] = len(issues)
        data_sources.extend(["forecasts", "anomalies", "invoice_issues"])

    elif intent == "OUT_OF_SCOPE":
        context["available_data"] = (
            "None. The question requests external or out-of-scope information "
            "not present in ArthX internal financial intelligence records."
        )

    return context, data_sources


# ── Query Execution Pipeline ─────────────────────────────────────────────────

def answer_user_query(db: Session, question: str) -> Dict[str, Any]:
    """
    End-to-end assistant pipeline:
      1. Classify intent
      2. Fetch relevant database records
      3. Generate grounded answer via Groq LLM
      4. Return typed response
    """
    intent, target_vendor = classify_intent(question)
    context, data_sources = fetch_grounded_context(db, intent, target_vendor)

    answer = generate_assistant_response(
        question=question,
        intent=intent,
        context_data=context,
    )

    return {
        "question": question,
        "intent": intent,
        "answer": answer,
        "data_sources": data_sources,
        "context_summary": {k: v for k, v in context.items() if k not in ("recent_transactions",)},
    }
