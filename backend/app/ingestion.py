from typing import Any, Dict, Union

from app.chunking import chunk_document_items
from app.clean_data import clean_extracted_items
from app.db.chroma_intergration import DEFAULT_COLLECTION, upsert_chunks
from app.embedding import embed_texts
from app.extract_data import extract_data


def ingest_document(
    pdf_source: Union[str, bytes, bytearray],
    doc_id: str,
    user_id: str,
    analyze_vlm: bool = False,
    collection_name: str = DEFAULT_COLLECTION,
) -> Dict[str, Any]:
    """
    Run the full ingestion pipeline for a PDF:
    extract -> clean -> chunk -> embed -> upsert into Chroma.
    """
    extracted_items = extract_data(
        pdf_source=pdf_source,
        analyze_vlm=analyze_vlm,
    )
    # deduplicacy
    cleaned_items = clean_extracted_items(extracted_items)
    if not cleaned_items:
        return {
            "doc_id": doc_id,
            "user_id": user_id,
            "extracted_count": len(extracted_items),
            "cleaned_count": 0,
            "chunk_count": 0,
            "upserted_count": 0,
        }

    chunks = chunk_document_items(
        extracted_items=cleaned_items,
        pdf_source=pdf_source,
    )

    chunks = [c for c in chunks if c.get("content", "").strip()]
    if not chunks:
        return {
            "doc_id": doc_id,
            "user_id": user_id,
            "extracted_count": len(extracted_items),
            "cleaned_count": len(cleaned_items),
            "chunk_count": 0,
            "upserted_count": 0,
        }

    texts = [c["content"] for c in chunks]
    embeddings = embed_texts(texts)

    upserted_count = upsert_chunks(
        chunks=chunks,
        embeddings=embeddings,
        doc_id=doc_id,
        user_id=user_id,
        collection_name=collection_name,
    )

    return {
        "doc_id": doc_id,
        "user_id": user_id,
        "extracted_count": len(extracted_items),
        "cleaned_count": len(cleaned_items),
        "chunk_count": len(chunks),
        "upserted_count": upserted_count,
    }


# Backward-compatible alias
ingestion = ingest_document
