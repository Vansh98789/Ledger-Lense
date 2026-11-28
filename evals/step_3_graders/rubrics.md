# Scoring Rubrics & Judgment Criteria

This document defines the automated grading rubrics for evaluating the LedgerLens RAG pipeline.

---

## 1. Retrieval Relevance Grader

### Objective
Verify that the retrieval pipeline fetched chunks containing the required evidence to answer the query.

### Primary Rule (Deterministic Hit@K)
- **PASS (1.0):** At least one chunk in the top-$K$ ($K=5$) retrieved results has `page_number == expected_page`.
- **FAIL (0.0):** None of the top-$K$ chunks match the expected page.
- **N/A:** If `expected_page` is `null` (unanswerable / negative query), PASS requires `len(retrieved_chunks) == 0` (router correctly bypassed retrieval).

### Semantic Context Relevance (LLM Judge)
- Evaluates whether the retrieved text snippet actually contains the facts needed to answer the question, or just co-occurring keywords.
- **Score 1 (Relevant):** The text explicitly contains the specific financial metric or statement.
- **Score 0 (Irrelevant):** The text is generic narrative text that mentions the entity but lacks the target data.

---

## 2. Answer Correctness Grader (Factual Accuracy)

### Objective
Verify that the generated answer matches the verified ground truth without hallucination, extrapolation, or loss of precision.

### Binary Pass/Fail Criteria
- **PASS (1.0):**
  - The answer states the exact financial quantity, unit, and direction (increase/decrease) as specified in `ground_truth_answer`.
  - All tokens in `must_include` are present.
  - For unanswerable queries: the model explicitly states that the filing does not contain this information.
- **FAIL (0.0):**
  - **Aggressive Rounding:** Rounding exact million figures into single-decimal billions (e.g., reporting `$2,717 million` as `$2.7 billion` is an automatic FAIL).
  - Any token in `must_not_include` is present.
  - Inverted direction (confusing 2023 with 2024, or increase with decrease).
  - Incorrect accounting sign (confusing negative expense `(62)` with positive income).

---

## 3. Faithfulness Grader (Groundedness / Hallucination Detection)

### Objective
Verify that every factual claim made in the generated answer is directly derived from the retrieved context chunks (zero parametric hallucinations).

### Scoring Rules
- **PASS (1.0):** Every number, date, entity, and assertion in the generated answer can be traced directly to an explicit statement in the retrieved context chunks.
- **FAIL (0.0):** The answer introduces facts, statistics, or predictions not found in the context (even if factually true in the real world from training memory).

---

## 4. Coherence & Directness Grader

### Objective
Verify the answer is concise, professional, and free from conversational filler.

### Criteria
- The response states the answer directly in the first sentence.
- Does not use filler phrases: *"Based on the provided documents...", "I found that..."*.
- Clearly cites the page and table source.
