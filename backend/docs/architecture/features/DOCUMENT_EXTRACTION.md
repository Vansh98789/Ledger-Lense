# DOCUMENT EXTRACTION ARCHITECTURE
====================================================

## Objectives
Financial filings (10-K, 10-Q, annual reports) contain dense narrative text, multi-column disclosures, complex multi-line tables, charts, and sometimes scanned legacy pages. 

The extraction pipeline must convert raw PDFs into high-fidelity structured chunks while **preserving bounding box coordinates (`bbox: [x0, y0, x1, y1]`) and cell references** for exact citation highlighting.

---

## 1. Input Types & Tooling Strategy

| Content Type | Primary Tool | Fallback / Alternative | Purpose & Details |
| :--- | :--- | :--- | :--- |
| **Typed Text & Layout** | `PyMuPDF` (`fitz`) | `pdfplumber` | Fast native text extraction with precise word/line coordinates, reading order reconstruction, and font size metadata (to detect headings). |
| **Multi-Column Text** | `PyMuPDF` (layout blocks) | `Docling` / `pdfplumber` | Resolves multi-column financial layouts into correct reading order without interleaving adjacent columns (handled in text file only). |
| **Digital Financial Tables** | `pdfplumber` / `Camelot` | Vision Language Model (VLM) | Extracts bordered/borderless tables into structured 2D matrices (Markdown/CSV/JSON), preserving row headers and column hierarchy. |
| **Scanned Pages & OCR** | `Tesseract OCR` / `PyMuPDF` OCR | Cloud VLM (e.g. Gemini Flash) | Detects pages without embedded text streams and runs OCR to extract text + word bounding boxes. |
| **Charts, Figures & Scanned Tables** | Vision Language Model (VLM) | Multimodal API | Converts visual bar charts, pie charts, and visual tables into structured text summaries and JSON tables. |
| **Document Links & References**| `PyMuPDF` (`page.get_links()`) | Built-in PDF parser | Extracts native cross-references, internal footnotes, and external regulatory URLs. |

---

## 2. Extraction Pipeline Execution Details

### Step 0: Page Classification & Layout Inspection
For each page in the PDF:
1. **Text Density Check:**
   - Use `PyMuPDF` to inspect text length and character stream.
   - If character count < threshold (e.g. < 50 characters on a full page), classify as **Scanned Page** and route to OCR/VLM.
2. **Table & Graphic Region Detection:**
   - Detect table bounding boxes using `pdfplumber` or `Camelot` (lattice/stream heuristics).
   - Non-table regions are marked as **Narrative Text**.

---

### Step 1: text extractor 
   Find Page Width & Layout:
   It divides the page vertically down the middle (left half vs right half).

   Detect Full-Width Headers:
   Any header spanning across the page (like "Item 7. MD&A") is kept at the top as a section divider.

   Sort Columns Top-to-Bottom:

   It takes all text on the left half and sorts it top 
   →
   → bottom.
   Then it takes all text on the right half and sorts it top 
   →
   → bottom.
   This guarantees Column 1 is read completely before Column 2 starts (no jumbled "Z-reading").

   Filter Out Tables & Attach BBoxes:

   It checks if any text block falls inside a table rectangle (ignore_rects). If yes, it skips it (to prevent duplicates).
   For every remaining paragraph, it saves { "text": ..., "page_number": ..., "bbox": [x0, y0, x1, y1] } for citation highlighting.

---

### Step 2: Structured Table Extraction & Cell Mapping
Financial tables require cell-level coordinates so citations can point to specific numbers:
Find Table Boundaries:
Uses page.find_tables() to detect grids and whitespace-aligned columns, recording the whole table's bounding box bbox: [x0, y0, x1, y1].

Validate (Financial Check):
Runs is_valid_financial_table():

Rejects false tables (e.g., long prose columns with >35 words per cell).
Ensures real financial numbers exist (requires numbers, $, or %).

Format for AI (Markdown):
Converts 2D table cells into a clean Markdown table (| Metric | 2023 | ... |) so LLMs and embeddings understand the relationships easily.

Map Every Cell (For Citations):
Tags each data point with its row name, column name, and value (e.g., Row: "Total net sales", Col: "2023", Val: "$383,285"), enabling clickable cell-level citations.
4. use pymypdf ove camelot because:
   -Speed (10x – 50x Difference)
   -Camelot Struggles with Borderless Tables
   -Camelot Requires Ghostscript (Deployment & Docker Headache)
   -Bounding Box & Coordinate Mismatch

---

### Step 3: Text Chunking with Layout Awareness
Traditional character-based naive chunking destroys financial context. We use **Layout-Aware Chunking**:
1. **Header-Aware Splitting:** Split text at structural boundaries (Item 1, Item 7 - MD&A, Financial Statements, Notes to Consolidated Financial Statements).
2. **Self-Contained Chunks:** Keep subsections together with their parent heading injected into the chunk metadata (e.g., `Section: Liquidity and Capital Resources > Note 3: Revenue Recognition`).
3. **Chunk Overlap & Coordinate Preservation:**
   - Maximum chunk size: ~500 to 1,000 tokens.
   - Overlap: ~100 tokens.
   - Every chunk retains its starting page, ending page, and bounding box union for highlighting.

---

## 3. Storage Schema in Neon PostgreSQL (`pgvector`)

Each chunk is stored with rich metadata to empower the retrieval and citation system:

```sql
CREATE TABLE document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    doc_id UUID NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    chunk_type VARCHAR(20) NOT NULL, -- 'text', 'table', 'chart'
    page_number INTEGER NOT NULL,
    bbox JSONB NOT NULL,             -- {"x0": 54.2, "y0": 120.5, "x1": 500.1, "y1": 210.3}
    table_metadata JSONB,           -- {"table_id": "T1", "row": 4, "col": 2, "header": "Revenue"}
    content TEXT NOT NULL,          -- Markdown table or text passage
    embedding VECTOR(1536),         -- pgvector embedding
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX ON document_chunks USING hnsw (embedding vector_cosine_ops);
CREATE INDEX ON document_chunks (doc_id, user_id);
```
