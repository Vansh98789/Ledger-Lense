# Chunking

Each content type is chunked differently. All chunks carry `page_number`, `bbox`, `metadata`, and `content`.

---

## Types

### Text
- Group blocks page-by-page until `max_words_per_chunk` (default 300) is hit
- 1 block overlap between chunks (sliding window)
- `bbox` = union of all blocks in the chunk

### Table
- ≤ 12 rows → 1 chunk (table kept intact)
- \> 12 rows → sliding window slices of 12 rows, 1 row overlap, header repeated in every slice
- `bbox` proportionally interpolated from row position

### Chart / Image
- 1 chart = 1 chunk, 1 image = 1 chunk
- No splitting, no overlap
- Decorative images (no financial data) are dropped

### Scanned / OCR Text
- Same grouping as text (word count ceiling)
- Each chunk tracks `average_confidence` (Tesseract 0–100)
- If `avg_confidence < 65.0` → crop exact chunk bbox from PDF → resend to VLM
- `method` field: `tesseract` | `vlm_fallback` | `vlm_targeted_rescan`

---

## Entry Point

```python
# backend/app/chunking/__init__.py
chunk_document_items(extracted_items, pdf_source=None, ...)
```

Accepts the full extracted list, fans it out to all 5 chunkers (each self-filters by `type`), then sorts output by `(page_number, bbox.y0)`.

```python
# backend/app/chunking.py  — thin wrapper for clean imports
from app.chunking import chunk_document_items

def chunk(extracted_items, pdf_source=None, **kwargs):
    return chunk_document_items(extracted_items, pdf_source=pdf_source, **kwargs)
```

---

## Parameters

| Parameter | Default | Applies to |
|---|---|---|
| `max_text_words` | 300 | text, scanned |
| `max_table_rows` | 12 | table |
| `text_overlap_blocks` | 1 | text, scanned |
| `table_overlap_rows` | 1 | table |
| `ocr_confidence_threshold` | 65.0 | scanned |

---

## Chunk Schema

```json
{
  "chunk_type": "text | table | chart | image | scanned_text",
  "page_number": 1,
  "bbox": [x0, y0, x1, y1],
  "content": "...",
  "metadata": {}
}
```
