"""
ArthX Assistant Schemas — T3.3
Pydantic models for the Conversational Assistant endpoint.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AssistantQueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="User's natural language question")


class AssistantQueryResponse(BaseModel):
    question: str
    intent: str
    answer: str
    data_sources: List[str] = Field(default_factory=list)
    context_summary: Optional[Dict[str, Any]] = None
