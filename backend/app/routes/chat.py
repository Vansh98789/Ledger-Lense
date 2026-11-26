from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.auth import get_current_user
from app.retreival import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatRequest(BaseModel):
    query: str
    doc_ids: Optional[List[str]] = None


class CitationOut(BaseModel):
    chunk_id: Optional[str] = None
    doc_id: Optional[str] = None
    page_number: Optional[int] = None
    chunk_type: Optional[str] = None
    bbox: Optional[List[float]] = None
    rerank_score: Optional[float] = None


class ChatResponse(BaseModel):
    answer: str
    confidence: str
    citations: List[CitationOut]


@router.post("/", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    user_id: str = Depends(get_current_user),
):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    result: Dict[str, Any] = answer_question(
        query=req.query,
        user_id=user_id,
        doc_ids=req.doc_ids,
    )

    return ChatResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        citations=[CitationOut(**c) for c in result.get("citations", [])],
    )
