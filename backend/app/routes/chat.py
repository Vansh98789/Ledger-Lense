import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.postgres import ChatMessage, ChatSession, get_db
from app.retreival import answer_question
from app.retrieval.generator import summarize_messages

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/chat", tags=["chat"])

RECENT_WINDOW = 5
SUMMARIZE_THRESHOLD = 1


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


class ChatHistoryItem(BaseModel):
    id: str
    role: str
    content: str
    confidence: Optional[str] = None
    citations: List[CitationOut] = []


def _get_or_create_session(db: Session, user_id: str) -> ChatSession:
    session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
    if not session:
        session = ChatSession(user_id=user_id)
        db.add(session)
        db.commit()
        db.refresh(session)
    return session


def _update_summary_if_needed(session_id: str, db_url: str) -> None:
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    try:
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            return

        query = db.query(ChatMessage).filter(ChatMessage.session_id == session_id)
        if session.last_summarized_at is not None:
            query = query.filter(ChatMessage.created_at > session.last_summarized_at)

        unsummarized = query.order_by(ChatMessage.created_at.asc()).all()
        if len(unsummarized) < RECENT_WINDOW + SUMMARIZE_THRESHOLD:
            return

        to_summarize = unsummarized[:-RECENT_WINDOW]
        msg_dicts = [{"role": m.role, "content": m.content} for m in to_summarize]
        session.summary = summarize_messages(session.summary, msg_dicts)
        session.last_summarized_at = to_summarize[-1].created_at
        db.commit()
    except Exception:
        logger.exception("Failed to summarize chat session %s", session_id)
        db.rollback()
    finally:
        db.close()
        engine.dispose()


@router.get("/history", response_model=List[ChatHistoryItem])
def get_chat_history(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.query(ChatSession).filter(ChatSession.user_id == user_id).first()
    if not session:
        return []

    rows = (
        db.query(ChatMessage)
        .filter(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )
    items: List[ChatHistoryItem] = []
    for m in rows:
        parsed_citations: List[CitationOut] = []
        if m.citations:
            try:
                parsed_citations = [CitationOut(**c) for c in json.loads(m.citations)]
            except (json.JSONDecodeError, TypeError):
                parsed_citations = []
        items.append(
            ChatHistoryItem(
                id=m.id,
                role=m.role,
                content=m.content,
                confidence=m.confidence,
                citations=parsed_citations,
            )
        )
    return items


@router.post("/", response_model=ChatResponse)
def chat(
    req: ChatRequest,
    background_tasks: BackgroundTasks,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not req.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    session = _get_or_create_session(db, user_id)

    msg_query = db.query(ChatMessage).filter(ChatMessage.session_id == session.id)
    if session.last_summarized_at is not None:
        msg_query = msg_query.filter(ChatMessage.created_at > session.last_summarized_at)
    recent = msg_query.order_by(ChatMessage.created_at.asc()).all()
    history = [{"role": m.role, "content": m.content} for m in recent]

    result: Dict[str, Any] = answer_question(
        query=req.query,
        user_id=user_id,
        doc_ids=req.doc_ids,
        summary=session.summary,
        history=history,
    )

    citations_raw = result.get("citations", [])
    db.add(
        ChatMessage(
            session_id=session.id,
            user_id=user_id,
            role="user",
            content=req.query,
        )
    )
    db.add(
        ChatMessage(
            session_id=session.id,
            user_id=user_id,
            role="assistant",
            content=result["answer"],
            confidence=result["confidence"],
            citations=json.dumps(citations_raw),
        )
    )
    db.commit()

    db_url = (
        os.getenv("DATABASE_URL")
        or f"sqlite:///{Path(__file__).resolve().parents[2] / 'ledgerlens.db'}"
    )
    background_tasks.add_task(_update_summary_if_needed, session.id, db_url)

    return ChatResponse(
        answer=result["answer"],
        confidence=result["confidence"],
        citations=[CitationOut(**c) for c in citations_raw],
    )
