# API Routes & Server Design

3 route groups + `/health`. All `/documents` and `/chat` routes require `Authorization: Bearer <token>`.

---

## 1. Auth — `/api/auth`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/signup` | Create user (bcrypt hash) in Neon `users`, return JWT |
| POST | `/signin` | Verify credentials, return JWT |

```json
{ "access_token": "<jwt>", "token_type": "bearer" }
```

- **Auth guard:** One shared `get_current_user` dependency (`Depends`) decodes the JWT and injects `user_id` — never trust `user_id` from request body.

---

## 2. Documents — `/api/documents`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/upload` | Validate PDF → save → insert `QUEUED` → trigger `BackgroundTasks` → return `202` |
| GET | `/{doc_id}/status` | Poll processing status (`QUEUED` \| `EXTRACTING` \| `COMPLETED` \| `FAILED`) |
| GET | `/` | List current user's uploaded documents |

**Upload flow:**
1. Validate early: `.pdf` extension/MIME, `%PDF-` magic bytes, max size (25MB)
2. Save via `storage.py` (`backend/data/` in dev, Cloudflare R2 when `R2_*` env vars are set) under `users/{user_id}/docs/{doc_id}/{filename}`
3. Insert row in Neon `documents` (`status = QUEUED`), return `202 Accepted` + `doc_id`
4. `BackgroundTasks` runs `ingest_document()` in threadpool → updates `EXTRACTING → COMPLETED` (or `FAILED` + `error_message` on exception)

---

## 3. Chat — `/api/chat`

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/` | Ask a question → `answer_question()` → answer + citations |

```json
// Request
{ "query": "What was Q3 revenue?", "doc_ids": ["<doc_id>"] }

// Response
{
  "answer": "Q3 revenue was $142.3M...",
  "confidence": "HIGH",
  "citations": [
    { "chunk_id": "...", "doc_id": "...", "page_number": 7, "chunk_type": "table", "bbox": [...], "rerank_score": 2.16 }
  ]
}
```

---

## 4. Health & Startup (`main.py`)

- `GET /health` — healthcheck endpoint for Docker/Render
- **`lifespan` warmup:** pre-loads `get_embedding_model()` and `get_reranker_model()` once at server startup so models stay in RAM across all requests
- **`CORSMiddleware`:** enabled for frontend origin

---

## Production Design Rules

| Concern | How It's Handled |
|---|---|
| **Event-loop blocking** | Sync routes (`/chat`, `/auth`, `/status`) use `def` so FastAPI runs them in the 40-thread pool instead of blocking `async` |
| **Neon idle sleep** | SQLAlchemy `pool_pre_ping=True` + `pool_recycle=300` (using Neon `-pooler` URL) auto-reconnects after 5-min idle |
| **Local → Cloud storage** | `storage.py` + `chroma_intergration.py` switch from local disk to R2 / Chroma Cloud via `.env` |
| **Error safety** | Background ingestion wraps in `try/except` to record `FAILED` + `error_message` |

---

## Storage Split

| Data | Where |
|---|---|
| Users + document metadata | Neon PostgreSQL (`users`, `documents`) |
| Raw PDFs | Cloudflare R2 (dev: `backend/data/`) |
| Chunk vectors | Chroma (`ledgerlens_chunks`) |
