# Embedding

Converts text/table/chart/image chunks and user queries into dense vectors for Neon `pgvector` similarity search.

---

## Model Choice

| Setting | Value |
|---|---|
| Library | `fastembed` (ONNX Runtime, no PyTorch) |
| Model | `BAAI/bge-small-en-v1.5` |
| Dimensions | `384` |


**Why this model:**
- Zero API cost and no rate limits
- Lightweight ONNX runtime (~130MB), safe for free-tier Docker containers
- Strong retrieval quality on English financial text and markdown tables

---

## API (`backend/app/embedding.py`)

- `embed_texts(texts, batch_size=64)` — batch-embeds chunks during ingestion, returns `List[List[float]]`
- `embed_query(query)` — embeds a single user question for retrieval (`model.query_embed` applies BGE query prefixing automatically)
- `get_embedding_model()` — lazy singleton so the ONNX model loads once per process

---

## Notes

- Neon `document_chunks.embedding` must be `VECTOR(384)` to match this model.
- Vectors alone struggle on exact years (`2023`), tickers, and line-item codes — pair with keyword/full-text search in `retreival.py`.
