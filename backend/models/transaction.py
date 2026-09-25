import enum
from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Enum
from sqlalchemy.sql import func
from database import Base

class TransactionType(str, enum.Enum):
    INFLOW = "inflow"
    OUTFLOW = "outflow"

class TransactionStatus(str, enum.Enum):
    NORMAL = "normal"
    FLAGGED = "flagged"
    REVIEWED = "reviewed"

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    vendor = Column(String(255), nullable=False, index=True)
    category = Column(String(255), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    type = Column(Enum(TransactionType), nullable=False)
    status = Column(Enum(TransactionStatus), default=TransactionStatus.NORMAL, nullable=False)
    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "vendor": self.vendor,
            "category": self.category,
            "amount": self.amount,
            "type": self.type.value if hasattr(self.type, "value") else str(self.type),
            "status": self.status.value if hasattr(self.status, "value") else str(self.status),
            "description": self.description,
        }
