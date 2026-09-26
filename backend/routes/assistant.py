"""
ArthX Assistant Routes — T3.3
Exposes POST /api/assistant/query for natural language financial queries.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from schemas.assistant import AssistantQueryRequest, AssistantQueryResponse
from services.assistant import answer_user_query

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/query", response_model=AssistantQueryResponse)
def query_assistant(
    request: AssistantQueryRequest,
    db: Session = Depends(get_db),
):
    """
    T3.3 — Conversational Assistant query endpoint:
    Accepts natural language questions, routes intent, fetches relevant
    ground-truth financial data, and returns an LLM answer grounded in real numbers.
    """
    try:
        result = answer_user_query(db=db, question=request.question)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Assistant query failed: {str(e)}")
