# 01. Failure Mode Analysis & Error Taxonomy

## Executive Summary
- **Benchmark Doc:** Tesla Q3 2024 Shareholder Update (`TSLA-Q3-2024-Update.pdf`)
- **Test Set:** 50 probe queries (25 retrieval-focused, 25 generation-focused)
- **Baseline Retrieval Hit@5:** **52.0% (26 / 50)**
- **Total Failures Flagged:** **27 / 50 (54.0%)** logged to [`failure_log.csv`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_1_failure_analysis/failure_log.csv)
- **Core Diagnosis:** Semantic search favors narrative text (Pages 3, 31) over tables (Pages 4, 6, 27). Generator aggressively rounds millions to single-decimal billions.

---

## Failure Taxonomy

| Failure Mode | Layer | Count | % | Symptom |
|---|---|:---:|:---:|---|
| **1. Narrative Bias Over Tables** | Hybrid Search | 16 | 59.3% | Pages 3 & 31 outranked financial statements on Pages 4, 6, 27. |
| **2. Aggressive Rounding** | Generator Prompt | 5 | 18.5% | Rounded exact millions ($2,717M, $338M) into billions ($2.7B, $0.3B). |
| **3. Unwarranted Refusal** | Context Packing / Prompt | 3 | 11.1% | Stated "Not found" even when the chunk was in the top 5 context. |
| **4. Multi-Row Table Splits** | Chunking | 3 | 11.1% | Rows needed for arithmetic were split across chunk boundaries. |

---

## Concrete Failure Examples

### 1. Narrative Bias (TC_025) — Retrieval Miss
- **Query:** *"What was Tesla's total assets balance at September 30, 2024?"*
- **Expected:** `$119,852 million USD` (Page 27)
- **Retrieved Pages:** `[31, 7, 9, 10, 1]` *(Page 27 missed)*
- **Output:** *"Not found in the document."*
- **Fix:** Increase BM25 keyword weight for balance sheet terms (`assets`, `liabilities`, `balance sheet`).

### 2. Aggressive Rounding (TC_007 & TC_036) — Generation Flaw
- **Query:** *"What was Income from Operations in Q3 2024?"*
- **Expected:** `$2,717 million USD` | **Output:** `"$2.7 billion"`
- **Query:** *"Difference between Non-GAAP and GAAP net income?"*
- **Expected:** `$338 million USD` | **Output:** `"$0.3 billion (~$300M)"` *(Lost $38M)*
- **Fix:** Add prompt rule: *"Report exact numeric figures as printed in text; never round millions to billions."*

### 3. Unwarranted Refusal (TC_017 & TC_020) — Context Dilution
- **Query:** *"Installed annual capacity for Model 3/Y at Shanghai factory?"*
- **Expected:** `>950,000 vehicles annually` (Page 7)
- **Retrieved Pages:** `[7, 10, 9, 8, 3]` *(Page 7 was present at rank #1)*
- **Output:** *"Not found in the document."*
- **Fix:** Calibrate QA refusal prompt to scan all chunks before defaulting to refusal.

### 4. Arithmetic Row Split (TC_046) — Chunking Flaw
- **Query:** *"Calculate Q3 2024 current assets less current liabilities."*
- **Expected:** `$25,802 million USD ($56,379M - $30,577M)` (Page 27)
- **Output:** *"Not found in the document."*
- **Fix:** Keep balance sheet tables in unified chunks with header metadata preserved.

---

## Action Plan for Steps 2 & 3
1. **Retrieval Tuning:** Boost BM25 weighting and expand retrieval candidates from $K=10$ to $K=15$ before reranking.
2. **Prompt Hardening:** Enforce strict financial precision rules (no rounding, no mental math, scan full context).
3. **Step 2 Golden Set Requirements:** 100+ questions balanced across:
   - 35% Financial tables & multi-column lookups
   - 25% Numerical precision probes (millions vs billions)
   - 20% Compound row arithmetic
   - 20% Out-of-scope refusal tests
