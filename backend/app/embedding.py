from typing import List, Optional
from fastembed import TextEmbedding

EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
EMBEDDING_DIM = 384

_model: Optional[TextEmbedding] = None


def get_embedding_model() -> TextEmbedding:
    global _model
    if _model is None:
        _model = TextEmbedding(model_name=EMBEDDING_MODEL)
    return _model


def embed_texts(texts: List[str], batch_size: int = 64) -> List[List[float]]:
    if not texts:
        return []
    model = get_embedding_model()
    return [vec.tolist() for vec in model.embed(texts, batch_size=batch_size)]


def embed_query(query: str) -> List[float]:
    model = get_embedding_model()
    vec = next(model.query_embed(query))
    return vec.tolist()
