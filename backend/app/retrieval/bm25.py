import re
from typing import Any, Dict, List, Optional

from rank_bm25 import BM25Okapi

from app.db.chroma_intergration import DEFAULT_COLLECTION, fetch_chunks_by_filter


# convert to lowercase punctuation free words
def tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def bm25_search(
    query: str,
    user_id: str,
    doc_ids: Optional[List[str]] = None,
    top_k: int = 10,
    collection_name: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:
    chunks = fetch_chunks_by_filter(
        user_id=user_id,
        doc_ids=doc_ids,
        collection_name=collection_name,
    )
    if not chunks:
        return []

    query_tokens = tokenize(query)
    if not query_tokens:
        return []

    corpus_tokens = [tokenize(c["content"]) for c in chunks]
    bm25 = BM25Okapi(corpus_tokens)
    scores = bm25.get_scores(query_tokens)

    scored_indices = sorted(
        range(len(chunks)),
        key=lambda i: scores[i],
        reverse=True,
    )

    results: List[Dict[str, Any]] = []
    for idx in scored_indices[:top_k]:
        if scores[idx] <= 0:
            continue
        chunk = dict(chunks[idx])
        chunk["bm25_score"] = round(float(scores[idx]), 4)
        results.append(chunk)

    return results
