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
