import enum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum
from sqlalchemy.sql import func
from database import Base

class InvoiceStatus(str, enum.Enum):
    PAID = "paid"
    PENDING = "pending"
    DISPUTED = "disputed"

class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    vendor = Column(String(255), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    invoice_date = Column(Date, nullable=False, index=True)
    due_date = Column(Date, nullable=False)
    status = Column(Enum(InvoiceStatus), default=InvoiceStatus.PENDING, nullable=False)
    po_reference = Column(String(100), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "vendor": self.vendor,
            "amount": self.amount,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "po_reference": self.po_reference,
        }
