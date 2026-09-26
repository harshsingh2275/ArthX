"""
ArthX Anomaly Schemas — T3.2
Pydantic models for anomaly read endpoints.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict


class AnomalyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: Optional[int] = None
    transaction_id: int
    vendor: str
    amount: float
    risk_score: float
    reason_code: str
    trigger_metric: str
    explanation: Optional[str] = None
    impact_on_30d_forecast: Optional[float] = None
    created_at: Optional[str] = None
