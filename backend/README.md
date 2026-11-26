# LedgerLens 🔍

AI-powered financial document Q&A backend. Upload a PDF (balance sheet, invoice, annual report) and ask questions in plain English. Gets back answers with page-level citations.

---

## Architecture

```
PDF Upload
   │
   ▼
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  Extraction  │───▶│   Chunking   │───▶│  Embedding   │
│  (PyMuPDF,   │    │  (by type:   │    │  (fastembed  │
│  Tesseract,  │    │  text/table/ │    │  bge-small)  │
│  Groq VLM)   │    │  chart/image)│    └──────┬───────┘
└──────────────┘    └──────────────┘           │
                                               ▼
                                        ┌──────────────┐
                                        │  ChromaDB    │
                                        │  (cosine     │
                                        │   HNSW)      │
                                        └──────┬───────┘
                                               │
Question ──────────────────────────────────────▼
   │                                    ┌──────────────┐
   │                                    │Hybrid Search │
   │                                    │ Vector + BM25│
   │                                    └──────┬───────┘
   │                                           │
   │                                    ┌──────▼───────┐
   │                                    │  Reranker    │
   │                                    │ (MiniLM L6)  │
   │                                    └──────┬───────┘
   │                                           │
   └──────────────────────────────────▶ ┌──────▼───────┐
                                        │  Groq LLM    │
                                        │  (JSON out)  │
                                        └──────┬───────┘
                                               │
                                        Answer + Citations
```

---

## Key Design Decisions

| Decision | Why |
|---|---|
| **`def` routes (not `async def`)** | PyMuPDF, Tesseract, ONNX models are CPU-bound. `def` runs in FastAPI's threadpool (40 threads) so the event loop is never blocked. |
| **Hybrid retrieval (Vector + BM25)** | Vector search finds semantically similar chunks; BM25 catches exact financial terms (`EBITDA`, ticker symbols). Both results are merged then reranked. |
| **Chunk by content type** | Text, tables, charts, and scanned pages each have different optimal chunking strategies — one-size chunking loses table structure. |
| **SQLite locally → Neon on deploy** | Zero-config local dev (`DATABASE_URL` unset = SQLite). Set `DATABASE_URL` in `.env` to switch to Neon without code changes. |
| **Local disk → R2 for PDFs** | Same `storage.py` interface. Local by default, switches to Cloudflare R2 when `R2_*` env vars are set. No code changes required. |

---

## Stack

| Layer | Technology |
|---|---|
| API | FastAPI + Uvicorn |
| Extraction | PyMuPDF, Tesseract-OCR, Groq VLM |
| Embedding | fastembed `BAAI/bge-small-en-v1.5` (384d, ONNX) |
| Reranker | fastembed `Xenova/ms-marco-MiniLM-L-6-v2` (ONNX) |
| Vector DB | ChromaDB (local) → Chroma Cloud (prod) |
| BM25 | rank-bm25 |
| LLM | Groq |
| Relational DB | SQLite (dev) → Neon PostgreSQL (prod) |
| PDF Storage | Local disk (dev) → Cloudflare R2 (prod) |
| Auth | PyJWT + bcrypt |

---

## Setup (Local Dev)

### Prerequisites
- Python 3.13+
- [uv](https://docs.astral.sh/uv/) — `pip install uv`
- Tesseract OCR — [download](https://github.com/UB-Mannheim/tesseract/wiki) and add to PATH
- A [Groq API key](https://console.groq.com/keys)

### Install & Run

```powershell
# 1. Clone and enter backend
cd backend

# 2. Install dependencies
uv sync

# 3. Copy env template and fill in values
cp .env.example .env
# Edit .env — at minimum set GROQ_API_KEY and JWT_SECRET

# 4. Start the server
python main.py
# → http://localhost:8000
# → http://localhost:8000/docs  (Swagger UI)
```

---

## API Routes

| Method | Route | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | — | Health check |
| `POST` | `/api/auth/signup` | — | Create account → `{message, email}` |
| `POST` | `/api/auth/signin` | — | Login → `{access_token}` |
| `POST` | `/api/documents/upload` | ✅ | Upload PDF → 202 + `doc_id` (ingestion runs in background) |
| `GET` | `/api/documents/` | ✅ | List user's documents |
| `GET` | `/api/documents/{doc_id}/status` | ✅ | Ingestion status (`PENDING / PROCESSING / COMPLETED / FAILED`) |
| `POST` | `/api/chat/` | ✅ | Ask a question → `{answer, confidence, citations}` |

All protected routes require `Authorization: Bearer <token>` header.

---

## Environment Variables

See [`.env.example`](.env.example) for the full list with descriptions.

**Required to run:**
- `GROQ_API_KEY`
- `JWT_SECRET` (≥ 32 random chars)

**Optional (defaults to local):**
- `DATABASE_URL` — Neon PostgreSQL URL for prod
- `CHROMA_API_KEY` / `CHROMA_TENANT` / `CHROMA_DATABASE` — Chroma Cloud
- `R2_*` — Cloudflare R2 for PDF storage
- `FRONTEND_ORIGIN` — CORS allow-list (default: `http://localhost:3000`)

---

## Deploy (Render)

1. Push to GitHub
2. Create a new **Web Service** on [Render](https://render.com)
3. Set **Root Directory** → `backend`
4. Set **Build Command** → `uv sync`
5. Set **Start Command** → `uvicorn main:app --host 0.0.0.0 --port $PORT`
6. Add all env vars from `.env.example` in Render's Environment tab
7. Set `DATABASE_URL` to your Neon pooler URL

Or use the included `Dockerfile` for Docker-based deploys.

---

## Project Structure

```
backend/
├── main.py                  # FastAPI app, lifespan, CORS, routers
├── pyproject.toml
├── Dockerfile
├── .env.example
├── app/
│   ├── config/settings.py   # Env var loading
│   ├── auth.py              # JWT + bcrypt helpers
│   ├── storage.py           # PDF save/load (local ↔ R2)
│   ├── extract_data.py      # Extraction orchestrator
│   ├── ingestion.py         # Full ingest pipeline
│   ├── retreival.py         # Retrieval re-export
│   ├── embedding.py         # fastembed wrapper
│   ├── clean_data.py        # Dedup + overlap filter
│   ├── extraction/          # text, table, chart, image, ocr extractors
│   ├── chunking/            # per-type chunkers
│   ├── retrieval/           # hybrid search, reranker, generator
│   ├── db/
│   │   ├── postgres.py      # SQLAlchemy models + session
│   │   └── chroma_intergration.py
│   ├── routes/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   └── chat.py
│   └── prompts/v1/          # LLM prompt templates
└── docs/architecture/       # Design docs per feature
```
