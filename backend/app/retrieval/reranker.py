from typing import Any, Dict, List, Optional

from fastembed.rerank.cross_encoder import TextCrossEncoder

RERANKER_MODEL = "Xenova/ms-marco-MiniLM-L-6-v2"

_reranker: Optional[TextCrossEncoder] = None


def get_reranker_model() -> TextCrossEncoder:
    global _reranker
    if _reranker is None:
        _reranker = TextCrossEncoder(model_name=RERANKER_MODEL)
    return _reranker


def rerank_chunks(
    query: str,
    chunks: List[Dict[str, Any]],
    top_k: int = 5,
) -> List[Dict[str, Any]]:
    if not chunks:
        return []

    reranker = get_reranker_model()
    documents = [c["content"] for c in chunks]
    scores = list(reranker.rerank(query, documents))

    ranked = sorted(
        zip(chunks, scores),
        key=lambda pair: pair[1],
        reverse=True,
    )

    results: List[Dict[str, Any]] = []
    for chunk, score in ranked[:top_k]:
        item = dict(chunk)
        item["rerank_score"] = round(float(score), 4)
        results.append(item)

    return results
