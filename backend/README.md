backend/
├── main.py                 ← starts the API server, defines routes only
├── pyproject.toml          ← dependencies (uv)
├── uv.lock
├── .env                    ← API keys (in .gitignore)
│
├── app/
│   ├── __init__.py
│   ├── config.py           ← ALL settings in one place
│   ├── ingestion.py        ← load PDF → clean text → chunk
│   ├── embeddings.py       ← turn chunks into vectors
│   ├── vector_store.py     ← save and search vectors (Chroma/FAISS)
│   ├── retriever.py        ← given a question, return top_k chunks
│   ├── prompts.py          ← prompt text lives here
│   ├── llm.py              ← calls the LLM
│   └── rag.py              ← ask(question): ties everything together
│
├── data/
│   ├── raw/                ← your original documents
│   └── vectordb/           ← saved index (in .gitignore)
│
├── scripts/
│   └── build_index.py      ← run once: ingest documents, build vector DB
│
└── docs/                   ← your architecture notes (keep as is)