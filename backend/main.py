import os
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.db.postgres import init_db
from app.embedding import get_embedding_model
from app.retrieval.reranker import get_reranker_model
from app.routes import auth_router, chat_router, documents_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- Startup: create tables + warm up local ONNX models once ---
    init_db()
    get_embedding_model()
    get_reranker_model()
    yield
    # --- Shutdown: nothing to clean up ---


app = FastAPI(
    title="LedgerLens API",
    description="Financial document AI — extract, chunk, embed, and answer with citations.",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS — allow frontend origin (update in production)
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router)
app.include_router(documents_router)
app.include_router(chat_router)


@app.get("/health", tags=["health"])
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
