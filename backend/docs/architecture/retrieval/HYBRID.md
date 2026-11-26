# Hybrid Search

Combines **semantic vector search** and **exact keyword search (BM25)** so neither meaning nor exact financial numbers/tickers get missed.

---

## Why Both?

| Search Type | Strong At | Weak At |
|---|---|---|
| **Vector (Chroma)** | Paraphrases & concepts (*"profitability"* ↔ *"gross margin"*) | Exact years (`2023`), tickers (`AAPL`), line-item codes |
| **BM25 (`rank_bm25`)** | Exact words, numbers, dates, table headers | Synonyms or differently phrased questions |

---

# bm25 working priciple =>
1. How often the query word appears in the chunk -> A chunk containing "invoice" 3 times scores higher than a chunk containing "invoice" once.

2. How rare the word is across all chunks -> Specific, rare words (like "402", "compressor", or "warranty") add a lot of points when they match.

3. Chunk length ->If two chunks both mention "compressor" once, the shorter, more focused chunk gets a higher score than a massive, rambling chunk.


## How `hybrid_search()` Works ([hybrid.py](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/backend/app/retrieval/hybrid.py))

1. **Vector branch:** `embed_query(query)` → `query_chunks(..., top_k=10)` from Chroma
2. **BM25 branch:** `fetch_chunks_by_filter(user_id, doc_ids)` → tokenize (`[a-z0-9]+`) → `BM25Okapi` → top 10 with score > 0
3. **Deduplicate:** Merge both lists by chunk `id` (up to 20 unique chunks)
   - Chunks found by both keep both `vector_score` and `bm25_score`
   - `retrieval_sources` records `["vector"]`, `["bm25"]`, or `["vector", "bm25"]`
4. **Handoff:** Deduplicated candidates go to `rerank_chunks()` to pick the final top 5
