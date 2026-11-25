# Pipeline

End-to-end flow from PDF upload to answered question.

---

## 1. Ingestion

```
User uploads PDF
    │
    ▼
Backend streams file → Cloudflare R2
    key: users/{user_id}/docs/{doc_id}/{filename}
    │
    ▼
Insert row into documents table (status = QUEUED)
    │
    ▼
Return 202 Accepted + doc_id  ←── frontend starts polling /status
    │
    ▼
Background task starts
    ├── status = EXTRACTING
    ├── Download PDF bytes from R2
    ├── Run extract_data() → typed items (text, table, chart, image, scanned_text)
    ├── Run chunk_document_items() → chunks with bbox + metadata
    ├── Embed each chunk (embedding model)
    ├── Bulk insert into document_chunks (Neon pgvector)
    └── status = COMPLETED  (or FAILED + error_message)
```

**Storage split:**
- Raw PDFs → Cloudflare R2 (binary, zero egress, 10GB free)
- Chunks + embeddings → Neon PostgreSQL pgvector (free tier)

---

## 2. Query

```
User question
    │
    ▼
Query Rewriter → resolves follow-ups, classifies intent
    │
    ▼
Hybrid Retrieval (pgvector cosine + keyword filter)
    scoped by: user_id + doc_id(s)
    │
    ▼
Agent Tools
    ├── calculator_tool   (deterministic Python math)
    └── table_cell_lookup (row + col → exact value)
    │
    ▼
Hallucination guardrail
    every cited number must exist in retrieved chunks
    if not → "Not found in the document"
    │
    ▼
Stream answer (SSE) + citation JSON
    { page_number, bbox, table_id, cell_ref, value }
```

---

## Key APIs

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/documents/upload` | POST | Upload PDF, trigger ingestion |
| `/api/documents/{doc_id}/status` | GET | Poll processing status |
| `/api/chat` | POST | Ask a question, receive SSE stream |
