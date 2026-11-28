# 03. Evaluation Graders & LLM Judge Prompts

## 1. Executive Summary
- **Purpose:** Replace manual inspection with automated, reproducible evaluation graders.
- **Grader Suite:**
  1. **Deterministic Retrieval Grader:** Computes Hit@5 and Mean Reciprocal Rank (MRR) with zero LLM overhead.
  2. **Strict Correctness Grader:** Hybrid rule-filter + LLM judge that penalizes rounding and factual drifts.
  3. **Faithfulness Grader:** Strict hallucination detector verifying claims against retrieved context blocks.
- **Implementation:** [`evals/step_3_graders/grader_engine.py`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_3_graders/grader_engine.py)

---

## 2. Grader Specifications

### A. Retrieval Grader (`grade_retrieval`)
- **Metric:** Hit@5 (Binary 1/0) and Reciprocal Rank ($1 / \text{rank}$).
- **Mechanism:** Pure Python string/int comparison against `chunk.metadata["page_number"]`.
- **Latency & Cost:** `< 0.001s`, **$0.00** (Zero LLM calls).

### B. Answer Correctness Grader (`grade_correctness`)
- **Inputs:** `question`, `generated_answer`, `ground_truth`, `must_not_include`.
- **Rule Layer:** If answer contains forbidden rounded strings (e.g. `"$14.5 billion"` instead of `"$14,530 million"`), it triggers an **instant FAIL**.
- **Judge Layer:** Evaluates whether numerical amounts, currencies, and directions match the ground truth.
- **Prompt:** [`evals/step_3_graders/prompts/correctness.txt`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_3_graders/prompts/correctness.txt)

### C. Faithfulness Grader (`grade_faithfulness`)
- **Inputs:** `generated_answer`, `retrieved_chunks`.
- **Rule:** Every statement in the answer must be derived from the context. Real-world facts not present in the retrieved chunks are labeled **UNFAITHFUL**.
- **Prompt:** [`evals/step_3_graders/prompts/faithfulness.txt`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/evals/step_3_graders/prompts/faithfulness.txt)

---

## 3. How Step 3 Targets Discovered Step 1 Failures

| Step 1 Failure Mode | Grader Defense Mechanism |
|---|---|
| **Narrative Bias Over Tables** | Retrieval grader flags any run where balance sheet or statement pages are missed in top-5 chunks. |
| **Aggressive Rounding ($2.7B vs $2,717M)** | Correctness grader prompt explicitly commands the judge to fail rounded figures that erase million-dollar precision. |
| **Unwarranted Refusals** | Faithfulness grader verifies whether a refusal was legitimate (context truly lacked data) or unwarranted. |

---

## 4. Next Step: Step 4 (Judge Validation)
Before we trust these automated LLM judges to grade our entire 100-question benchmark, we must **validate the judges themselves** against human labels to ensure high scoring agreement (>85%).
