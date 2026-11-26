from typing import Any, Dict, List, Optional

from app.db.chroma_intergration import DEFAULT_COLLECTION
from app.retrieval.generator import generate_answer
from app.retrieval.hybrid import hybrid_search
from app.retrieval.reranker import rerank_chunks


def retrieve(
    query: str,
    user_id: str,
    doc_ids: Optional[List[str]] = None,
    vector_k: int = 10,
    bm25_k: int = 10,
    top_k: int = 5,
    collection_name: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:

    candidates = hybrid_search(
        query=query,
        user_id=user_id,
        doc_ids=doc_ids,
        vector_k=vector_k,
        bm25_k=bm25_k,
        collection_name=collection_name,
    )
    return rerank_chunks(query=query, chunks=candidates, top_k=top_k)


def answer_question(
    query: str,
    user_id: str,
    doc_ids: Optional[List[str]] = None,
    vector_k: int = 10,
    bm25_k: int = 10,
    top_k: int = 5,
    collection_name: str = DEFAULT_COLLECTION,
    prompt_version: str = "v1",
) -> Dict[str, Any]:

    chunks = retrieve(
        query=query,
        user_id=user_id,
        doc_ids=doc_ids,
        vector_k=vector_k,
        bm25_k=bm25_k,
        top_k=top_k,
        collection_name=collection_name,
    )
    return generate_answer(
        question=query,
        chunks=chunks,
        prompt_version=prompt_version,
    )
