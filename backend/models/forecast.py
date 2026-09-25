from sqlalchemy import Column, Integer, String, Float, Date, DateTime, Text
from sqlalchemy.sql import func
from database import Base

class Forecast(Base):
    __tablename__ = "forecasts"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, index=True)
    predicted_net_flow = Column(Float, nullable=False)
    lower = Column(Float, nullable=False)
    upper = Column(Float, nullable=False)
    horizon_days = Column(Integer, default=30)
    trend_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())

    def to_dict(self):
        return {
            "id": self.id,
            "date": self.date.isoformat() if self.date else None,
            "predicted_net_flow": self.predicted_net_flow,
            "lower": self.lower,
            "upper": self.upper,
            "horizon_days": self.horizon_days,
            "trend_summary": self.trend_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
