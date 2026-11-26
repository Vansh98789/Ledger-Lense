# Pipeline

End-to-end flow from PDF upload to answered question — reflecting actual implementation.

---

## 1. Ingestion (`app/ingestion.py`)

```
User uploads PDF
    │
    ▼
Backend streams file → Cloudflare R2
    key: users/{user_id}/docs/{doc_id}/{filename}
    │
    ▼
Insert row into documents table (status = QUEUED)
Return 202 Accepted + doc_id  ←── frontend polls /status
    │
    ▼
Background task: ingest_document(pdf_bytes, doc_id, user_id)
    │
    ├── extract_data(pdf_bytes, analyze_vlm=False)
    │       ├── Per page: is_scanned_page()?
    │       │       Yes → Tesseract OCR → avg_confidence < 65% → Groq VLM fallback
    │       │       No  → tables → charts → images → text (skipping ignore_rects)
    │       └── Returns: List[{type, page_number, bbox, content, metadata}]
    │
    ├── clean_extracted_items()
    │       ├── Drop empty content
    │       ├── Drop exact per-page duplicates (normalized text key)
    │       └── Drop text blocks overlapping ≥70% with table/chart/image bbox
    │
    ├── chunk_document_items(cleaned_items, pdf_source)
    │       ├── text        → word-count groups (≤300 words), 1 block overlap
    │       ├── table       → ≤12 rows = 1 chunk, >12 rows = sliding window + header repeat
    │       ├── chart       → 1 chart = 1 chunk
    │       ├── image       → 1 image = 1 chunk (decorative dropped)
    │       └── scanned_text → word-count groups + VLM crop rescan if avg_conf < 65%
    │
    ├── embed_texts([chunk.content for chunk in chunks])
    │       └── BAAI/bge-small-en-v1.5 (fastembed, ONNX) → 384-dim vectors
    │
    ├── upsert_chunks(chunks, embeddings, doc_id, user_id)
    │       └── Chroma collection: ledgerlens_chunks
    │           metadata: doc_id, user_id, chunk_type, page_number, bbox, metadata
    │
    └── status = COMPLETED  (or FAILED + error_message)
```

**Storage:**
- Raw PDFs → Cloudflare R2 (binary, zero egress, 10GB free)
- Chunk vectors → Chroma (`ledgerlens_chunks`, cosine HNSW, local dev / Cloud on deploy)

---

## 2. Query → Answer (`app/retrieval/`)

```
User question
    │
    ▼
answer_question(query, user_id, doc_ids)
    │
    ├── hybrid_search(query, user_id, doc_ids)
    │       ├── embed_query(query) → 384-dim vector
    │       ├── query_chunks(vector, top_k=10)      → Chroma cosine search
    │       ├── bm25_search(query, top_k=10)         → BM25Okapi exact keyword search
    │       └── deduplicate by chunk id → up to 20 unique candidates
    │           (chunks found by both: carry vector_score + bm25_score)
    │
    ├── rerank_chunks(candidates, top_k=5)
    │       └── Xenova/ms-marco-MiniLM-L-6-v2 (fastembed cross-encoder, ONNX)
    │           scores each (query, chunk) pair → keep top 5 by rerank_score
    │
    ├── generate_answer(question, top_5_chunks)
    │       ├── format_context() → numbered chunk blocks with type + page
    │       ├── Groq LLM (openai/gpt-oss-120b, temp=0.0)
    │       │   system: prompts/v1/qa_v1.txt (strict grounding rules)
    │       │   returns JSON: {answer, confidence, used_chunk_indices}
    │       └── assemble citations from used_chunk_indices
    │           {chunk_id, doc_id, page_number, chunk_type, bbox, rerank_score}
    │
    └── Response
            {answer, confidence, citations, retrieved_chunks}
```

**All queries strictly scoped by `user_id` and optional `doc_ids` (multi-tenant isolation).**

---

## Key APIs (Planned)

| Endpoint | Method | Purpose |
|---|---|---|
| `POST /api/documents/upload` | POST | Upload PDF → R2 → trigger background ingestion |
| `GET /api/documents/{doc_id}/status` | GET | Poll `QUEUED / EXTRACTING / COMPLETED / FAILED` |
| `POST /api/chat` | POST | Ask a question → SSE streamed answer + citations |
