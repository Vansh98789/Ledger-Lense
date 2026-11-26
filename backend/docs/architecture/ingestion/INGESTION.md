# Ingestion Pipeline

Orchestrates the end-to-end flow from raw PDF to searchable vectors in Chroma ([ingestion.py])

---

## Flow

```text
PDF (path or bytes)
    │
    ▼
1. extract_data()           → typed items (text, table, chart, image, scanned_text)
    │                         [see DOCUMENT_EXTRACTION.md]
    ▼
2. clean_extracted_items()  → drops empty items, per-page exact duplicates,
    │                         and text blocks overlapping ≥70% with tables/charts/images
    ▼
3. chunk_document_items()   → type-specific chunks with bbox + metadata
    │                         [see CHUNKING.md]
    ▼
4. embed_texts()            → 384-dim vectors via BAAI/bge-small-en-v1.5
    │                         [see EMBEDDING.md]
    ▼
5. upsert_chunks()          → stored in Chroma (local or Cloud) scoped by user_id + doc_id
                              [see CHROMA.md]
```

---

## Entry Point

```python
ingest_document(
    pdf_source,
    doc_id="...",
    user_id="...",
    analyze_vlm=False,
    collection_name="ledgerlens_chunks",
)
```

- Returns `{"doc_id", "user_id", "extracted_count", "cleaned_count", "chunk_count", "upserted_count"}`
- Exits early with `0` counts if extraction or cleaning produces no items
- Deterministic IDs (`{doc_id}_{index}`) in Chroma make re-running ingestion idempotent

---

## Related Docs

- [DOCUMENT_EXTRACTION.md](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/backend/docs/architecture/features/DOCUMENT_EXTRACTION.md)
- [CHUNKING.md](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/backend/docs/architecture/features/CHUNKING.md)
- [EMBEDDING.md](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/backend/docs/architecture/features/EMBEDDING.md)
- [CHROMA.md](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/backend/docs/architecture/features/CHROMA.md)
