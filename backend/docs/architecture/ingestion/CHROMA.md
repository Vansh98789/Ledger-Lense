# Chroma Vector Store

Stores embedded document chunks and runs multi-tenant similarity search.

---

## Local vs Cloud

Controlled by `.env` in `get_chroma_client()` ([chroma_intergration.py](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/backend/app/db/chroma_intergration.py)):

- **Local (default):** `PersistentClient` saves to `backend/chroma_db/` (gitignored, zero config)
- **Cloud (deploy):** Set `CHROMA_API_KEY`, `CHROMA_TENANT`, and `CHROMA_DATABASE` in `.env` → automatically uses `CloudClient`

---

## Collection & Schema

- **Collection:** `ledgerlens_chunks` (`hnsw:space = cosine`)
- **Chunk ID:** `{doc_id}_{index}` (deterministic, so re-ingesting overwrites cleanly)

Chroma metadata only accepts flat primitives (`str`, `int`, `float`, `bool`), so `bbox` and `metadata` are stored as JSON strings:

| Field | Type | Purpose |
|---|---|---|
| `doc_id` | `str` | Document identifier |
| `user_id` | `str` | Multi-tenant isolation filter |
| `chunk_type` | `str` | `text` \| `table` \| `chart` \| `image` \| `scanned_text` |
| `page_number` | `int` | Source PDF page for citations |
| `bbox` | `str` (JSON) | `[x0, y0, x1, y1]` highlight box |
| `metadata` | `str` (JSON) | Extra chunk info (table cells, OCR confidence, etc.) |

---

## Functions

- `upsert_chunks(chunks, embeddings, doc_id, user_id)` — batches (100/call) into Chroma
- `query_chunks(query_embedding, user_id, doc_ids=None, top_k=8)` — cosine search strictly filtered by `user_id` (and optional `doc_ids`), parses `bbox`/`metadata` back to Python objects, returns `score = 1 - distance`
- `delete_document_chunks(doc_id, user_id)` — deletes all chunks for a document
