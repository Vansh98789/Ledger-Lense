# COMPLETE PIPELINE ARCHITECTURE
==================================================

## Overview
LedgerLens processes financial PDF documents (10-K, 10-Q, annual reports) to answer financial questions with verified citations down to the page, table, and cell, running calculations deterministically in code.

---

## 1. Document Ingestion & Storage Pipeline

### Step 1: Authentication & Upload
1. The user logs in (JWT / session-based auth). Multi-tenant isolation is strictly enforced via `user_id`.
2. The user uploads a PDF file (or selects a sample report from the library).
3. The backend receives the file stream:
   - **Binary Storage:** Stream the raw PDF directly to **Cloudflare R2** (S3-compatible, zero egress fees, 10 GB free tier) under the key:
     `users/{user_id}/docs/{doc_id}/{filename}`
   - **Database Record:** Insert a row into the Neon PostgreSQL `documents` table:
     - `id`: UUID (Primary Key)
     - `user_id`: UUID (Foreign Key)
     - `filename`: Text
     - `r2_key`: S3/R2 storage key
     - `status`: `QUEUED` (Enum: `QUEUED`, `EXTRACTING`, `INDEXING`, `COMPLETED`, `FAILED`)
     - `page_count`: Integer (initially NULL)
     - `error_message`: Text (nullable)
     - `created_at`: Timestamp

### Step 2: Asynchronous Background Processing
4. The API immediately responds with `202 Accepted` and the `doc_id` / `process_id`.
5. Background processing kicks off (via FastAPI `BackgroundTasks` or async task runner):
   - **Update Status:** Status changes to `EXTRACTING`.
   - **Download Stream:** Read PDF bytes directly from Cloudflare R2 into memory or temporary buffer.
   - **Parsing & Extraction:** Run the hybrid parser (PyMuPDF for layout/text + pdfplumber/VLM for tables and scanned content).
   - **Coordinate Preservation:** Every paragraph, table, and data point preserves its bounding box:
     `bbox: [x0, y0, x1, y1]` and `page_number`.
   - **Update Status:** Status changes to `INDEXING`.
   - **Embeddings & Vectorization:** Text and table chunks are embedded using an embedding model (e.g. `text-embedding-3-small` or open-source embeddings).
   - **Neon Storage:** Chunks and embeddings are bulk-inserted into the Neon PostgreSQL `document_chunks` table using `pgvector`.
   - **Update Status:** Status changes to `COMPLETED`. If an unhandled error occurs, status becomes `FAILED` with the exact error stored in `error_message`.

### Step 3: Frontend Polling / Progress Status
6. The frontend performs short polling (e.g., every 2 seconds to `GET /api/documents/{doc_id}/status`) until status is `COMPLETED` or `FAILED`.
7. Once `COMPLETED`, the document is marked active and ready for questioning.

---

## 2. Agent Query & Verification Pipeline

```text
User Question
      │
      ▼
[ 1. Query Rewriter & Router ]
   ├── Resolves conversational context / follow-ups
   └── Routes intent: (Direct Lookup vs Calculation vs Multi-Year Comparison)
      │
      ▼
[ 2. Hybrid Retrieval (Neon pgvector + Full-Text Search) ]
   ├── Scoped strictly by user_id and selected doc_id(s)
   └── Fetches top-k text chunks, tables, and cell metadata with bounding boxes
      │
      ▼
[ 3. Agent Reasoning & Tool Execution ]
   ├── Table Inspector Tool: Extracts structured rows/columns
   └── Calculator Tool: Executes Python code sandbox for ratios, growth, margins
      │
      ▼
[ 4. Self-Checking & Verification Guard ]
   ├── Grounding check: Did every cited number originate from retrieved chunks?
   ├── Unit & consistency check: Flags discrepancies or restatements
   └── Hallucination guard: If unsupported, forces "Not found in the document"
      │
      ▼
[ 5. Structured Response & Citation Assembly ]
   ├── Markdown stream to frontend with confidence score
   └── Clickable citations: { doc_id, page_number, bbox: [x0, y0, x1, y1], table_id, cell_ref }
```

### Step-by-Step Flow:
1. **User asks a question** via the chat interface (supports single doc or multi-doc comparison).
2. **Contextual Rewriter:** Resolves multi-turn references (e.g., *"What was their net income?"* followed by *"How did that compare to 2022?"* is rewritten with full context).
3. **Retrieval (Hybrid):** Neon DB executes vector cosine similarity (`pgvector`) combined with keyword filtering for exact ticker/metric terms. Returns matching chunks and bounding boxes.
4. **Tool Use & Code Execution:**
   - For mathematical calculations (growth %, operating margin, P/E ratio), the agent **never does mental math**.
   - It invokes the `calculator_tool`, running deterministic code, and returns both formula and result.
5. **Verification & Grounding Check:**
   - The agent cross-examines its generated answer against the source chunks.
   - If numbers cannot be strictly grounded in the document, it outputs: *"Not found in the document"*.
6. **Streaming & Citations:**
   - Answer streams token-by-token to the UI.
   - Accompanying JSON citation metadata is emitted. Clicking a citation jumps to the page in the PDF viewer and renders the highlight overlay using the stored bounding boxes.
