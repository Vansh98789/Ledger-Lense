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
    bm25_alpha: float = 0.35,
) -> List[Dict[str, Any]]:

    if not chunks:
        return []

    reranker = get_reranker_model()
    documents = [c["content"] for c in chunks]
    scores = list(reranker.rerank(query, documents))

    # Normalise BM25 scores to [0, 1] so they're on the same scale as rerank scores
    bm25_raw = [float(c.get("bm25_score", 0.0)) for c in chunks]
    max_bm25 = max(bm25_raw) if max(bm25_raw) > 0 else 1.0
    norm_bm25 = [s / max_bm25 for s in bm25_raw]

    # Blend: final = cross_encoder_score + alpha * normalised_bm25_bonus
    blended = [rs + bm25_alpha * nb for rs, nb in zip(scores, norm_bm25)]

    ranked = sorted(
        zip(chunks, blended),
        key=lambda pair: pair[1],
        reverse=True,
    )

    results: List[Dict[str, Any]] = []
    for chunk, score in ranked[:top_k]:
        item = dict(chunk)
        item["rerank_score"] = round(float(score), 4)
        results.append(item)

    return results
