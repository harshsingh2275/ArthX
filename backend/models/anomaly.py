from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.sql import func
from database import Base

class Anomaly(Base):
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id", ondelete="CASCADE"), nullable=False, index=True)
    vendor = Column(String(255), nullable=False)
    amount = Column(Float, nullable=False)
    risk_score = Column(Float, nullable=False, index=True)
    reason_code = Column(String(100), nullable=False)
    trigger_metric = Column(String(255), nullable=False)
    explanation = Column(Text, nullable=True)
    impact_on_30d_forecast = Column(Float, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "transaction_id": self.transaction_id,
            "vendor": self.vendor,
            "amount": self.amount,
            "risk_score": self.risk_score,
            "reason_code": self.reason_code,
            "trigger_metric": self.trigger_metric,
            "explanation": self.explanation,
            "impact_on_30d_forecast": self.impact_on_30d_forecast,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
