from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TransactionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    date: date
    vendor: str
    category: str
    amount: float
    type: str
    status: str
    description: Optional[str] = None
