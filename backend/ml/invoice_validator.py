"""
ArthX Invoice Validation Logic — T2.4

Implements automated audit checks on invoices:
  1. Duplicate Detection:
     Identifies and flags invoices with the same vendor and identical amount
     (within $0.01 tolerance) submitted within a 7-day window.
  2. Missing PO Reference:
     Flags invoices lacking a purchase order (PO) reference number, preventing
     unverified 3-way matching.

Pure validation logic (no database side effects).
Output contract matches T2.1 structure: {invoice_id, vendor, amount, issue_type, detail}.
"""

from dataclasses import dataclass
from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence
from collections import defaultdict


# ── Configuration Constants ──────────────────────────────────────────────────
DUPLICATE_WINDOW_DAYS: int = 7
AMOUNT_TOLERANCE: float = 0.01


class InvoiceIssueType(str, Enum):
    DUPLICATE_INVOICE = "DUPLICATE_INVOICE"
    MISSING_PO_REFERENCE = "MISSING_PO_REFERENCE"
    MISSING_PO = "MISSING_PO_REFERENCE"  # Alias for compatibility


@dataclass
class InvoiceValidationIssue:
    invoice_id: int
    vendor: str
    amount: float
    issue_type: str
    detail: str
    invoice_date: Optional[date] = None

    def to_contract(self) -> Dict[str, Any]:
        """
        Output contract structured similarly to T2.1 anomaly detection:
        Returns invoice_id, issue_type, detail string, plus vendor and amount.
        """
        return {
            "invoice_id": self.invoice_id,
            "vendor": self.vendor,
            "amount": round(self.amount, 2),
            "issue_type": self.issue_type,
            "detail": self.detail,
        }

    def to_dict(self) -> Dict[str, Any]:
        d = self.to_contract()
        if self.invoice_date:
            d["invoice_date"] = self.invoice_date.isoformat()
        return d


# ── Extraction & Parsing Helpers ─────────────────────────────────────────────

def _get_attr(obj: Any, key: str, default: Any = None) -> Any:
    """Safe getter supporting both dicts and SQLAlchemy ORM models."""
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _parse_date(val: Any) -> Optional[date]:
    """Parse various date formats (date, datetime, ISO string) into date."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        val = val.strip()
        if not val:
            return None
        # Support full ISO timestamp or simple YYYY-MM-DD
        if "T" in val:
            return datetime.fromisoformat(val).date()
        return date.fromisoformat(val)
    return None


def _parse_amount(val: Any) -> float:
    """Parse amount safely to float."""
    if val is None:
        return 0.0
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0


# ── Core Validation Logic ───────────────────────────────────────────────────

def find_duplicate_invoices(
    invoices: Sequence[Any],
    window_days: int = DUPLICATE_WINDOW_DAYS,
) -> List[InvoiceValidationIssue]:
    """
    Rule 1: Duplicate Detection
    Identifies invoices that have the same vendor and amount within a 7-day window.

    For each invoice involved in a duplicate pair/cluster, an issue is raised
    citing the specific matching invoice(s), dates, and day gap.
    """
    # Group valid records by vendor (case-insensitive)
    vendor_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

    for inv in invoices:
        inv_id = _get_attr(inv, "id")
        raw_vendor = _get_attr(inv, "vendor")
        amount = _parse_amount(_get_attr(inv, "amount"))
        inv_date = _parse_date(_get_attr(inv, "invoice_date"))

        if inv_id is None or not raw_vendor or inv_date is None:
            continue

        clean_vendor = str(raw_vendor).strip()
        vendor_groups[clean_vendor.lower()].append({
            "id": int(inv_id),
            "vendor": clean_vendor,
            "amount": amount,
            "date": inv_date,
            "raw": inv,
        })

    issues: List[InvoiceValidationIssue] = []

    for _, group in vendor_groups.items():
        if len(group) < 2:
            continue

        # Sort chronologically, then by ID
        group.sort(key=lambda x: (x["date"], x["id"]))

        # Check each invoice against all other invoices in this vendor group
        for i, a in enumerate(group):
            matches = []
            for j, b in enumerate(group):
                if i == j or a["id"] == b["id"]:
                    continue

                # Check identical amount within tolerance
                if abs(a["amount"] - b["amount"]) <= AMOUNT_TOLERANCE:
                    gap_days = abs((b["date"] - a["date"]).days)
                    if gap_days <= window_days:
                        matches.append({
                            "id": b["id"],
                            "date": b["date"],
                            "amount": b["amount"],
                            "gap_days": gap_days,
                        })

            if matches:
                # Format detailed grounded explanation
                if len(matches) == 1:
                    m = matches[0]
                    detail = (
                        f"Potential duplicate of invoice #{m['id']} (${m['amount']:,.2f} on {m['date'].isoformat()}): "
                        f"same vendor '{a['vendor']}' and identical amount submitted {m['gap_days']} day(s) apart."
                    )
                else:
                    match_strs = [
                        f"#{m['id']} on {m['date'].isoformat()} ({m['gap_days']}d gap)"
                        for m in matches
                    ]
                    detail = (
                        f"Potential duplicate of {len(matches)} invoices ({', '.join(match_strs)}): "
                        f"same vendor '{a['vendor']}' and identical amount (${a['amount']:,.2f}) within {window_days}-day window."
                    )

                issues.append(
                    InvoiceValidationIssue(
                        invoice_id=a["id"],
                        vendor=a["vendor"],
                        amount=a["amount"],
                        issue_type=InvoiceIssueType.DUPLICATE_INVOICE.value,
                        detail=detail,
                        invoice_date=a["date"],
                    )
                )

    return issues


def find_missing_po_invoices(
    invoices: Sequence[Any],
) -> List[InvoiceValidationIssue]:
    """
    Rule 2: Missing PO Reference
    Flags any invoices that are missing a PO reference.
    """
    issues: List[InvoiceValidationIssue] = []

    for inv in invoices:
        inv_id = _get_attr(inv, "id")
        raw_vendor = _get_attr(inv, "vendor")
        amount = _parse_amount(_get_attr(inv, "amount"))
        inv_date = _parse_date(_get_attr(inv, "invoice_date"))
        po_ref = _get_attr(inv, "po_reference")

        if inv_id is None:
            continue

        clean_vendor = str(raw_vendor).strip() if raw_vendor else "Unknown Vendor"

        # Check if PO is missing / blank / None / "null"
        is_missing = (
            po_ref is None
            or str(po_ref).strip() == ""
            or str(po_ref).strip().lower() in ("none", "null")
        )

        if is_missing:
            detail = (
                f"Missing purchase order reference: invoice #{inv_id} from '{clean_vendor}' "
                f"(${amount:,.2f}) has no PO number attached — cannot be matched for 3-way verification."
            )
            issues.append(
                InvoiceValidationIssue(
                    invoice_id=int(inv_id),
                    vendor=clean_vendor,
                    amount=amount,
                    issue_type=InvoiceIssueType.MISSING_PO_REFERENCE.value,
                    detail=detail,
                    invoice_date=inv_date,
                )
            )

    return issues


def validate_invoices(
    invoices: Sequence[Any],
    window_days: int = DUPLICATE_WINDOW_DAYS,
) -> List[InvoiceValidationIssue]:
    """
    Execute all invoice validation rules on the provided invoices.
    Returns combined list of issues sorted by invoice_id and issue_type.
    """
    duplicates = find_duplicate_invoices(invoices, window_days=window_days)
    missing_pos = find_missing_po_invoices(invoices)

    all_issues = duplicates + missing_pos
    all_issues.sort(key=lambda x: (x.invoice_id, x.issue_type))
    return all_issues


def run_invoice_validation(
    db: Any = None,
    invoices: Optional[Sequence[Any]] = None,
    window_days: int = DUPLICATE_WINDOW_DAYS,
) -> List[InvoiceValidationIssue]:
    """
    Convenience entrypoint: runs validation against provided list of invoices
    or queries all invoices from the provided DB session.
    """
    if invoices is None:
        if db is None:
            raise ValueError("Either 'invoices' or 'db' must be provided.")
        from models.invoice import Invoice
        invoices = db.query(Invoice).order_by(Invoice.invoice_date.asc(), Invoice.id.asc()).all()

    return validate_invoices(invoices, window_days=window_days)
