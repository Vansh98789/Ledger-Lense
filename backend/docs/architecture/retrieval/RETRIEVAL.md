# Retrieval & Answer Generation

Finds the top 5 most relevant chunks for a user question using hybrid search + reranking, then sends them to Groq LLM for a grounded answer.

---

## Flow

```text
User Question
    │
    ▼
0. check whether the retrival is need or not 
    │
    ▼
1. hybrid_search()     → 10 semantic (Chroma) + 10 keyword (BM25) → deduplicated (up to 20)
    │                    [see HYBRID.md]
    ▼
2. rerank_chunks()     → Cross-encoder (Xenova/ms-marco-MiniLM-L-6-v2, ONNX) → top 5
    │
    ▼
3. generate_answer()   → Groq LLM (openai/gpt-oss-120b) + qa_v1.txt prompt
    │                    Returns answer, confidence, citations
    ▼
4. Response            → { answer, confidence, citations: [page, bbox, chunk_type, ...] }
```

---

## Modules (`backend/app/retrieval/`)

| File | Responsibility |
|---|---|
| `bm25.py` | `bm25_search()` — exact keyword/number/ticker scoring via `BM25Okapi` |
| `hybrid.py` | `hybrid_search()` — Chroma vector + BM25, merge & deduplicate by chunk `id` |
| `reranker.py` | `rerank_chunks()` — lazy ONNX cross-encoder, outputs `rerank_score` per chunk |
| `generator.py` | `generate_answer()` — formats context, calls Groq, parses JSON, assembles citations |
| `__init__.py` | `retrieve()` and `answer_question()` — the two public entry points |

---

## Entry Points

```python
from app.retrieval import retrieve, answer_question

# Just retrieval (top 5 chunks)
chunks = retrieve(query, user_id, doc_ids=["..."])

# Full Q&A (retrieval + LLM answer)
result = answer_question(query, user_id, doc_ids=["..."])
```

---

## Response Schema (`answer_question`)

```json
{
  "answer": "Revenue was $142.3M in Q3, up 18% QoQ.",
  "confidence": "HIGH",
  "citations": [
    {
      "chunk_id": "doc_1_4",
      "doc_id": "doc_1",
      "page_number": 7,
      "chunk_type": "table",
      "bbox": [54.0, 180.0, 490.0, 220.0],
      "rerank_score": 2.1621
    }
  ],
  "retrieved_chunks": [...]
}
```

`confidence`: `HIGH` | `MEDIUM` | `LOW` | `NOT_FOUND`

---

## LLM Prompt (`prompts/v1/qa_v1.txt`)

Instructs the model to:
- Answer only from the retrieved context — no outside knowledge
- Return `"Not found in the document."` if context is insufficient
- Respond in strict JSON with `answer`, `confidence`, and `used_chunk_indices`

---

## Notes

- All queries are strictly scoped by `user_id` (multi-tenant isolation).
- If `chunks` is empty, `generate_answer()` skips the LLM call and returns `NOT_FOUND` immediately.
- Models load lazily once per process (`get_qa_llm()`, `get_reranker_model()`, `get_embedding_model()`).
- Default QA model: `openai/gpt-oss-120b` (changeable via `DEFAULT_QA_MODEL` in `generator.py`).
