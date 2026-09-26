from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class InvoiceIssue(Base):
    __tablename__ = "invoice_issues"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    issue_type = Column(String(100), nullable=False) # DUPLICATE_INVOICE, MISSING_PO
    detail = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "vendor": self.vendor,
            "amount": self.amount,
            "issue_type": self.issue_type,
            "detail": self.detail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    def to_contract(self):
        return {
            "invoice_id": self.invoice_id,
            "issue_type": self.issue_type,
            "detail": self.detail,
            "vendor": self.vendor,
            "amount": self.amount,
        }
