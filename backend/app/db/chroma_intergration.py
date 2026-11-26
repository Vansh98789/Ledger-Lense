import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection

DEFAULT_COLLECTION = "ledgerlens_chunks"
DEFAULT_CHROMA_PATH = Path(__file__).resolve().parents[2] / "chroma_db"

_client: Optional[ClientAPI] = None


def get_chroma_client() -> ClientAPI:

    global _client
    if _client is not None:
        return _client

    api_key = os.getenv("CHROMA_API_KEY")
    if api_key:
        _client = chromadb.CloudClient(
            api_key=api_key,
            tenant=os.getenv("CHROMA_TENANT"),
            database=os.getenv("CHROMA_DATABASE"),
        )
    else:
        DEFAULT_CHROMA_PATH.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(DEFAULT_CHROMA_PATH))

    return _client


def get_collection(collection_name: str = DEFAULT_COLLECTION) -> Collection:
    client = get_chroma_client()
    return client.get_or_create_collection(
        name=collection_name,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(
    chunks: List[Dict[str, Any]],
    embeddings: List[List[float]],
    doc_id: str,
    user_id: str,
    collection_name: str = DEFAULT_COLLECTION,
    batch_size: int = 100,
) -> int:
    if len(chunks) != len(embeddings):
        raise ValueError(
            f"chunks ({len(chunks)}) and embeddings ({len(embeddings)}) length mismatch"
        )
    if not chunks:
        return 0

    collection = get_collection(collection_name)
    total = len(chunks)

    for start in range(0, total, batch_size):
        end = start + batch_size
        batch_chunks = chunks[start:end]
        batch_embeddings = embeddings[start:end]

        ids = [f"{doc_id}_{start + i}" for i in range(len(batch_chunks))]
        documents = [c["content"] for c in batch_chunks]
        metadatas = [
            {
                "doc_id": str(doc_id),
                "user_id": str(user_id),
                "chunk_type": str(c.get("type", "unknown")),
                "page_number": int(c.get("page_number", 0)),
                "bbox": json.dumps(c.get("bbox", [])),
                "metadata": json.dumps(c.get("metadata", {}), default=str),
            }
            for c in batch_chunks
        ]

        collection.upsert(
            ids=ids,
            embeddings=batch_embeddings,
            documents=documents,
            metadatas=metadatas,
        )

    return total


def _build_where_filter(
    user_id: str, doc_ids: Optional[List[str]] = None
) -> Dict[str, Any]:
    """Build multi-tenant Chroma metadata filter."""
    if doc_ids:
        return {
            "$and": [
                {"user_id": str(user_id)},
                {"doc_id": {"$in": [str(d) for d in doc_ids]}},
            ]
        }
    return {"user_id": str(user_id)}


def _format_chunk(
    chunk_id: str,
    content: str,
    meta: Dict[str, Any],
    score: Optional[float] = None,
) -> Dict[str, Any]:
    """Normalize a Chroma record into the shared chunk dict format."""
    item: Dict[str, Any] = {
        "id": chunk_id,
        "doc_id": meta.get("doc_id"),
        "chunk_type": meta.get("chunk_type"),
        "page_number": meta.get("page_number"),
        "bbox": json.loads(meta.get("bbox", "[]")),
        "metadata": json.loads(meta.get("metadata", "{}")),
        "content": content,
    }
    if score is not None:
        item["score"] = score
    return item


# for retrieval
def query_chunks(
    query_embedding: List[float],
    user_id: str,
    doc_ids: Optional[List[str]] = None,
    top_k: int = 8,
    collection_name: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:
    """Query top-k chunks scoped strictly to user_id (and optional doc_ids)."""
    collection = get_collection(collection_name)
    where_filter = _build_where_filter(user_id, doc_ids)

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        where=where_filter,
        include=["documents", "metadatas", "distances"],
    )

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    dists = results.get("distances", [[]])[0]

    return [
        _format_chunk(chunk_id, content, meta, score=round(1.0 - float(dist), 4))
        for chunk_id, content, meta, dist in zip(ids, docs, metas, dists)
    ]


# fetching for bm25
def fetch_chunks_by_filter(
    user_id: str,
    doc_ids: Optional[List[str]] = None,
    collection_name: str = DEFAULT_COLLECTION,
) -> List[Dict[str, Any]]:
    collection = get_collection(collection_name)
    where_filter = _build_where_filter(user_id, doc_ids)

    results = collection.get(
        where=where_filter,
        include=["documents", "metadatas"],
    )

    ids = results.get("ids", [])
    docs = results.get("documents", [])
    metas = results.get("metadatas", [])

    return [
        _format_chunk(chunk_id, content, meta)
        for chunk_id, content, meta in zip(ids, docs, metas)
    ]


def delete_document_chunks(
    doc_id: str,
    user_id: str,
    collection_name: str = DEFAULT_COLLECTION,
) -> None:
    collection = get_collection(collection_name)
    collection.delete(
        where={
            "$and": [
                {"user_id": str(user_id)},
                {"doc_id": str(doc_id)},
            ]
        }
    )
