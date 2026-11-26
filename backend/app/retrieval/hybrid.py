from typing import Any, Dict, List, Optional

from app.db.chroma_intergration import DEFAULT_COLLECTION, query_chunks
from app.embedding import embed_query
from app.retrieval.bm25 import bm25_search


def hybrid_search(
    query: str,
    user_id: str,
    doc_ids: Optional[List[str]] = None,
    vector_k: int = 10,
    bm25_k: int = 10,
    collection_name: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:

    query_embedding = embed_query(query)
    vector_hits = query_chunks(
        query_embedding=query_embedding,
        user_id=user_id,
        doc_ids=doc_ids,
        top_k=vector_k,
        collection_name=collection_name,
    )
    bm25_hits = bm25_search(
        query=query,
        user_id=user_id,
        doc_ids=doc_ids,
        top_k=bm25_k,
        collection_name=collection_name,
    )

    merged: Dict[str, Dict[str, Any]] = {}

    for hit in vector_hits:
        cid = hit["id"]
        entry = dict(hit)
        entry["vector_score"] = entry.pop("score", 0.0)
        entry["retrieval_sources"] = ["vector"]
        merged[cid] = entry

    for hit in bm25_hits:
        cid = hit["id"]
        if cid in merged:
            merged[cid]["bm25_score"] = hit["bm25_score"]
            merged[cid]["retrieval_sources"].append("bm25")
        else:
            entry = dict(hit)
            entry["retrieval_sources"] = ["bm25"]
            merged[cid] = entry

    return list(merged.values())
