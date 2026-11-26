import uuid
from typing import List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.db.postgres import Document, get_db
from app.ingestion import ingest_document
from app.storage import load_pdf, save_pdf

router = APIRouter(prefix="/api/documents", tags=["documents"])

MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB


def _validate_pdf(data: bytes, filename: str) -> None:
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")
    if len(data) > MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail="File too large. Max 25MB.")
    if not data.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Invalid PDF file.")


def _run_ingestion(
    storage_key: str,
    doc_id: str,
    user_id: str,
    db_url: str,
) -> None:
    """Background task: load PDF bytes, ingest, update DB status."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.db.postgres import Document

    engine = create_engine(db_url, pool_pre_ping=True, pool_recycle=300)
    Session = sessionmaker(bind=engine)
    db = Session()
    try:
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if not doc:
            return

        doc.status = "EXTRACTING"
        db.commit()

        pdf_bytes = load_pdf(storage_key)
        if not pdf_bytes:
            raise FileNotFoundError("PDF not found in storage.")

        ingest_document(pdf_bytes=pdf_bytes, doc_id=doc_id, user_id=user_id)

        doc.status = "COMPLETED"
        db.commit()
    except Exception as exc:
        db.rollback()
        db = Session()
        doc = db.query(Document).filter(Document.id == doc_id).first()
        if doc:
            doc.status = "FAILED"
            doc.error_message = str(exc)[:500]
            db.commit()
    finally:
        db.close()
        engine.dispose()


class DocumentOut(BaseModel):
    id: str
    filename: str
    status: str
    error_message: Optional[str] = None

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    doc_id: str
    status: str


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_202_ACCEPTED)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    data = await file.read()
    _validate_pdf(data, file.filename or "")

    doc_id = str(uuid.uuid4())
    storage_key = f"users/{user_id}/docs/{doc_id}/{file.filename}"
    save_pdf(data, storage_key)

    doc = Document(
        id=doc_id,
        user_id=user_id,
        filename=file.filename or "upload.pdf",
        storage_key=storage_key,
        status="QUEUED",
    )
    db.add(doc)
    db.commit()

    import os
    db_url = os.getenv("DATABASE_URL") or f"sqlite:///{__import__('pathlib').Path(__file__).resolve().parents[2] / 'ledgerlens.db'}"
    background_tasks.add_task(_run_ingestion, storage_key, doc_id, user_id, db_url)

    return UploadResponse(doc_id=doc_id, status="QUEUED")


@router.get("/", response_model=List[DocumentOut])
def list_documents(
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    docs = db.query(Document).filter(Document.user_id == user_id).order_by(Document.created_at.desc()).all()
    return docs


@router.get("/{doc_id}/status", response_model=DocumentOut)
def get_document_status(
    doc_id: str,
    user_id: str = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    doc = db.query(Document).filter(Document.id == doc_id, Document.user_id == user_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found.")
    return doc
