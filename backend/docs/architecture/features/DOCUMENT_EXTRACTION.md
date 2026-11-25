# Document Extraction

Converts raw financial PDFs into structured, typed items — each with `page_number`, `bbox`, `content`, and `metadata`.

---

## Tools Used

| Content | Tool | Reason |
|---|---|---|
| Text & layout | PyMuPDF (`fitz`) | Fast, native coordinates, reading order |
| Tables | PyMuPDF `page.find_tables()` | Faster than Camelot, no Ghostscript needed, better borderless table support |
| Charts & figures | Groq VLM (vision) | Only tool that can interpret visual data |
| Scanned pages | Tesseract → Groq VLM fallback | Tesseract for speed; VLM when confidence < 65% |
| Images | Groq VLM (vision) | Classification + text transcription |

---

## Page-by-Page Flow (`extract_data.py`)

For every page:

1. **Scanned check** — `is_scanned_page()`: word count < 50 → route to OCR
2. **If digital:**
   - Extract tables → charts → images (collect their bboxes as `ignore_rects`)
   - Extract text, skipping anything inside `ignore_rects` (prevents duplicates)
3. **If scanned:** Tesseract OCR → if avg confidence < 65% → VLM fallback for the full page

Each extracted item has:
```json
{
  "type": "text | table | chart | image | scanned_text",
  "page_number": 1,
  "bbox": [x0, y0, x1, y1],
  "content": "...",
  "metadata": {}
}
```

---

## Extractor Details

### Text (`text_extract.py`)
- Splits page at midpoint → left column read top→bottom, then right column
- Full-width blocks (> 65% page width) treated as section headers
- Skips any block overlapping a table/chart/image bbox

### Tables (`table_extract.py`)
- `page.find_tables()` detects grid + borderless tables
- `is_valid_financial_table()` rejects false positives:
  - Any cell with > 35 words → not a table (it's prose)
  - < 15% numeric cell density → not a financial table
- Output: Markdown table + cell metadata (row label, col header, value)

### Charts (`chart_extractor.py`)
- Detects vector drawing clusters + raster image rects
- Crops region → sends image bytes to VLM with `vlm_chart_v1.txt` prompt
- VLM returns: markdown table of data points + plain-text summary

### Images (`image_extract.py`)
- Filters out images < 100×100px (icons/logos)
- VLM with `vlm_image_v1.txt`: classifies type, transcribes text, explains relevance

### Scanned OCR (`scan_ocr_extract.py`)
- Tesseract returns per-word confidence (0–100)
- If avg confidence < 65% → `_call_vlm_for_page()` with `vlm_ocr_v1.txt`

---

## Storage Schema (Neon PostgreSQL + pgvector)

```sql
CREATE TABLE document_chunks (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id      UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id     UUID NOT NULL,
    chunk_type  VARCHAR(20) NOT NULL,   -- text | table | chart | image | scanned_text
    page_number INTEGER NOT NULL,
    bbox        JSONB NOT NULL,         -- [x0, y0, x1, y1]
    metadata    JSONB,                  -- row/col refs, confidence, table_id, etc.
    content     TEXT NOT NULL,
    embedding   VECTOR(1536),
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON document_chunks (doc_id, user_id);
```
