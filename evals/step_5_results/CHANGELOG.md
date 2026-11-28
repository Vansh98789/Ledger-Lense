# Step 5 — Eval Iteration Log

> Tune on `dev_set.json` only. Write `notes/05_results.md` once all metrics hit **≥ 85%**.

## Targets vs Final Results (All Passed! 🎉)
| Metric | Target | Baseline | tuned_v3 (Final) | Status |
|---|---|---|---|---|
| **Retrieval Hit@5** | ≥ 85% | 52.0% (26/50) | **98.0% (49/50)** | ✅ **PASSED (+46.0%)** |
| **Retrieval MRR** | — | 0.285 | **0.786** | ✅ **+0.501** |
| **Answer Correctness** | ≥ 85% | 48.0% (12/25) | **96.0% (24/25)** | ✅ **PASSED (+48.0%)** |
| **Answer Faithfulness** | ≥ 85% | 56.0% (14/25) | **88.0% (22/25)** | ✅ **PASSED (+32.0%)** |

---

## baseline — 2026-11-28
- **Tag:** `baseline`
- **What Changed:** Nothing. Initial baseline run on unmodified pipeline.
- **Scores:** Hit@5: 52.0% | Correctness: 48.0% | Faithfulness: 56.0% | MRR: 0.285
- **File:** `runs/run_dev_baseline_20261128_133427.json`
- **Diagnosis:** 
  - 10 generation questions failed due to unwarranted "Not found" refusals caused by missing retrieval.
  - Page 4, 6, 27 tables were failing retrieval consistently because vector embeddings favored narrative pages over raw numerical tables.

---

## tuned_v1 — 2026-11-28
- **Tag:** `tuned_v1_increase_number_of_chunks`
- **What Changed:**
  - `backend/app/retrieval/__init__.py`: Increased candidate pool `vector_k=15`, `bm25_k=15` (from 10).
- **Scores:** Hit@5: 52.0% (No change)
- **Finding:** Increasing candidate count alone did not help because the missing table chunks were completely absent from initial top candidate rankings. Stopped early to conserve API quota.

---

## tuned_v2 — 2026-11-28
- **Tag:** `tuned_v2`
- **What Changed:**
  - `backend/app/retrieval/reranker.py`: Implemented hybrid CrossEncoder + BM25 score blending (`bm25_alpha=0.35`). Exact financial keywords now receive a direct boost over plain narrative text.
  - `backend/app/prompts/v2/qa_v2.txt`: Created version 2 prompt with strict precision rule (must state millions, never round to billions) and relaxed refusal condition (only refuse if topic is 100% absent).
- **Scores (Retrieval Partial):** Hit@5 jumped from 52.0% → 76.0% on first 25 questions (fixed TC_007, TC_009, TC_024).
- **Finding:** Identified deeper structural blocker on pages 4, 6, and 27 — PyMuPDF table extractor was dropping text labels and masking clean text blocks during ingestion.

---

## tuned_v3 — 2026-11-28 (The Target Smasher 🏆)
- **Tag:** `tuned_v3`
- **What Changed:**
  1. `backend/app/extract_data.py`: Removed table bounding boxes from `page_ignore_rects`. Clean text blocks on table pages are now fully preserved instead of being discarded.
  2. `backend/app/clean_data.py`: Removed text suppression for regions overlapping tables.
  3. **ChromaDB Re-ingestion:** Cleared stale `eval_tsla_q3_2024` collection and re-ingested with clean text chunks for financial tables (pages 4, 6, 26, 27, 28).
  4. **Active Prompt v2:** `qa_v2.txt` strictly enforcing million-dollar precision over billions and preventing false refusals.
- **Scores:**
  - **Retrieval Hit@5: 98.0% (49/50)** — (+46.0% over baseline)
  - **Retrieval MRR: 0.786** — (+0.501 over baseline)
  - **Answer Correctness: 96.0% (24/25)** — (+48.0% over baseline)
  - **Answer Faithfulness: 88.0% (22/25)** — (+32.0% over baseline)
- **File:** `runs/run_dev_tuned_v3_20261128_164019.json`
- **Conclusion:** **ALL 3 TARGET METRICS HIT (≥85%)**. RAG pipeline optimization for development dataset is COMPLETE. Ready for Step 5 Results documentation and frozen test set evaluation.
