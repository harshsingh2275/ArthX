"""
ArthX Forecast Schemas — T3.2
Pydantic models for forecast read endpoints.
"""

from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class ForecastPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: str
    predicted_net_flow: float
    lower: float
    upper: float


class ForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    horizon_days: int
    forecast: List[ForecastPointResponse]
    trend_summary: str
    method: Optional[str] = None
