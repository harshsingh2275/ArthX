from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    vendor: str
    amount: float
    invoice_date: date
    due_date: date
    status: str
    po_reference: Optional[str] = None


class InvoiceIssueContract(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    invoice_id: int
    vendor: str
    amount: float
    issue_type: str
    detail: str


class InvoiceIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    invoice_id: int
    vendor: str
    amount: float
    issue_type: str
    detail: str
    created_at: Optional[str] = None


class InvoiceValidationSummary(BaseModel):
    status: str
    total_invoices_scanned: int
    total_issues_found: int
    duplicate_count: int
    missing_po_count: int
    issues: list[InvoiceIssueContract]
