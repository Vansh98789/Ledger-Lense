# LedgerLens — Features

---

## Must Ship (Core)

### 1. Document Upload & Processing
- Upload financial PDFs (10-K, 10-Q, annual reports)
- Handles text, tables, charts, scanned pages (OCR)
- Background processing with status: `QUEUED → EXTRACTING → INDEXING → COMPLETED`
- Each user sees only their own documents

### 2. Chat / Q&A
- Streaming chat interface
- Single doc or multi-doc comparison (e.g. 3 years)
- Follow-up questions with conversation memory
- Returns "Not found in the document" instead of guessing

### 3. Verifiable Answers
- Every number links to: page, table, cell
- Calculations (margin, growth, ratios) run in code — formula shown to user
- Confidence indicator per answer (`HIGH / MEDIUM / LOW / NOT_FOUND`)

### 4. Evals
- 100+ question test set with known answers
- One command reruns the eval and reports accuracy + retrieval hit rate
- Automatic regression check — catches drops before they ship

---

## Strong Additions

### 5. Self-Checking
- Cross-checks numbers across sections (e.g. Net Income in P&L vs Cash Flow)
- Flags restated figures, unit mismatches, totals that don't add up

### 6. Reliability
- Retries, timeouts, clean error messages
- Cost and latency logged per request

### 7. Security
- Per-user data isolation (all queries scoped by `user_id`)
- API keys out of code (`.env` only)
- Prompt injection protection

---

## Stretch (Only If Time)
- Clickable PDF page with highlight overlay
- Export answer as summary with citations
- Admin dashboard (cost per query, slow queries, failures)
- Multi-document comparison UI
