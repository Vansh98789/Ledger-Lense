# 05. Evaluation Results (Step 5)

## 1. Score Summary

All 3 metrics surpassed the **≥85%** target:

| Metric | Target | Baseline | **tuned_v3 (Final)** | Delta | Status |
|---|---|---|---|---|---|
| **Retrieval Hit@5** | ≥ 85% | 52.0% | **98.0%** (49/50) | **+46.0%** | ✅ PASS |
| **Retrieval MRR** | — | 0.285 | **0.786** | **+0.501** | ✅ PASS |
| **Answer Correctness** | ≥ 85% | 48.0% | **96.0%** (24/25) | **+48.0%** | ✅ PASS |
| **Answer Faithfulness** | ≥ 85% | 56.0% | **88.0%** (22/25) | **+32.0%** | ✅ PASS |

---

## 2. Why Baseline Failed

1. **Table Text Masking (Ingestion):** PyMuPDF table finder detected tables on pages 4, 6, and 27, but stripped labels (e.g. Page 27 had numbers without row titles). The code then deleted the normal page text, so ChromaDB had **no words** for "Total assets" or "Operating income".
2. **Cross-Encoder Narrative Bias:** Reranker favored smooth prose (Page 3 "$2.7B") over raw table rows (Page 4 "2,717").
3. **Aggressive Refusals & Rounding:** Prompt `v1` returned `"Not found"` on slight context mismatch and rounded millions into billions (`$2.7B` vs `$2,717M`).

---

## 3. Fixes Applied

| Component | File | Change |
|---|---|---|
| **Ingestion** | `backend/app/extract_data.py` | Stopped deleting normal text when tables are detected. |
| **Cleaning** | `backend/app/clean_data.py` | Removed text-dropping rule for table regions. |
| **Database** | ChromaDB (`eval_tsla_q3_2024`) | Cleared corrupted chunks and re-ingested with clean text. |
| **Retrieval** | `backend/app/retrieval/reranker.py` | Added BM25 score blending (`alpha=0.35`) to boost exact financial keywords over narrative text. |
| **Prompt** | `backend/app/prompts/v2/qa_v2.txt` | Enforced strict millions notation (no billion rounding) and narrowed refusal rules. |

---

## 4. Key Case Comparison

| Test | Question | Baseline | tuned_v3 |
|---|---|---|---|
| **TC_025** | Total assets balance (p.27) | **FAIL** (Got pages 31, 7, 9) | **PASS** (Got page 27 at rank 2) |
| **TC_038** | Free cash flow calc (6,255 - 3,513) | **FAIL** (Rounded: "$2.7B") | **PASS** (Exact: "2,742 million USD") |
| **TC_040** | Total vehicle deliveries (p.6) | **FAIL** ("Not found in document") | **PASS** ("462,890 vehicles") |

---

## 5. Artifacts
- **Baseline Run:** [`evals/step_5_results/runs/run_dev_baseline_20261128_133427.json`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_5_results/runs/run_dev_baseline_20261128_133427.json)
- **Final Run:** [`evals/step_5_results/runs/run_dev_tuned_v3_20261128_164019.json`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_5_results/runs/run_dev_tuned_v3_20261128_164019.json)
- **Iteration Log:** [`evals/step_5_results/changelog.md`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_5_results/changelog.md)
