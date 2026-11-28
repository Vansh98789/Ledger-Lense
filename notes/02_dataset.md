# 02. Golden Dataset Design & Benchmark Split

## 1. Executive Summary
- **Source Document:** Tesla Q3 2024 Shareholder Update (`TSLA-Q3-2024-Update.pdf`, 31 pages).
- **Total Benchmark Size:** **100 Curated Financial Q&A Pairs**.
- **Dataset Split:** **50 Dev / 50 Test** (Symmetrical 50/50 partition).
- **Primary Objective:** Rigorously stress-test the 4 failure modes discovered in Step 1 (Narrative Bias, Aggressive Rounding, Unwarranted Refusal, and Table Boundary Splits).

---

## 2. Dev vs. Test Split Strategy

| Dataset Partition | File Location | Size | Role & Policy |
|---|---|:---:|---|
| **Development Set** | [`evals/step_2_dataset/dev_set.json`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_2_dataset/dev_set.json) | 50 Qs | **Iterative Tuning:** Used to experiment, optimize BM25/vector search weights, and refine generation prompts. Run frequently during bug fixing. |
| **Frozen Test Set** | [`evals/step_2_dataset/test_set.json`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_2_dataset/test_set.json) | 50 Qs | **Frozen Final Benchmark:** Locked out-of-sample set. Never tuned against. Run only at final evaluation to provide unbiased proof of generalization. |

---

## 3. Benchmark Category Distribution (100 Questions)

Both `dev_set` and `test_set` share an identical balance between **Retrieval** and **Generation** challenges:

| Target Stage | Category | Dev Set | Test Set | Total | Primary Failure Mode Targeted |
|---|---|:---:|:---:|:---:|---|
| **Retrieval** | `table_lookup` | 10 | 10 | **20** | Counteracts narrative bias (Statements of Operations, Balance Sheets). |
| **Retrieval** | `exact_acronym` | 8 | 8 | **16** | Tests BM25 precision on financial terms (GAAP, EPS, EBITDA, FCF). |
| **Retrieval** | `multi_section` | 4 | 4 | **8** | Tests multi-page retrieval (Energy Storage vs Auto Deliveries). |
| **Retrieval** | `semantic_paraphrase` | 3 | 3 | **6** | Tests dense vector search on non-keyword conceptual queries. |
| **Generation** | `numerical_precision` | 8 | 8 | **16** | Penalizes aggressive rounding ($2,717M vs $2.7B). |
| **Generation** | `accounting_notation` | 8 | 8 | **16** | Tests negative parentheses `(62)` and footnote multipliers. |
| **Generation** | `multi_row_arithmetic` | 5 | 5 | **10** | Tests derived ratio and delta calculations without hallucinations. |
| **Generation** | `unanswerable_refusal` | 4 | 4 | **8** | Tests proper refusal rate on out-of-scope / missing information. |
| **Total** | | **50** | **50** | **100** | |

---

## 4. Ground-Truth Quality Standards

To eliminate ambiguity in automated grading, every entry includes:
1. **`expected_retrieval.page`:** Printed PDF page number containing the evidence (or `null` for unanswerable queries).
2. **`ground_truth_answer`:** Exact factual answer verified directly against the SEC filing.
3. **`must_include`:** Key tokens that must appear in the answer (e.g., `["14,530", "million"]`).
4. **`must_not_include`:** Common hallucination or rounding pitfalls that trigger an immediate fail (e.g., `["14.5 billion"]`).

---

## 5. Anti-Bias & Contamination Controls
- **Model Asymmetry:** The benchmark questions were synthesized using a different model family (OpenAI GPT-4o) from the application's runtime model (Groq Llama/OSS), avoiding **self-preference bias**.
- **Human Verification:** All 100 numerical values were verified against the primary document tables to ensure 100% factual ground truth.
