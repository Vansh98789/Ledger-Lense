# EVALUATION, BENCHMARKING & REGRESSION TESTING
==================================================

## Overview
LedgerLens relies on rigorous quantitative evaluations. We track retrieval hit rate, hallucination rate, and numeric answer accuracy across a golden test suite of 100+ questions. Changes that regress accuracy below baseline are caught automatically.

---

## 1. Golden Evaluation Dataset Structure (`eval_dataset.json`)

The test set covers single filings, multi-year comparisons, complex tables, and negative examples (questions whose answers do not exist).

### Benchmark Schema:
```json
[
  {
    "id": "eval_001",
    "document": "Apple_FY23_10K.pdf",
    "category": "calculation", // "direct_lookup" | "calculation" | "multi_year" | "scanned_table" | "not_in_doc"
    "question": "What was Apple's gross margin percentage in fiscal year 2023?",
    "ground_truth_answer": "44.13%",
    "ground_truth_numeric": 44.13,
    "tolerance": 0.05, // Acceptable float difference (e.g. 44.1% - 44.2%)
    "requires_calculation": true,
    "expected_formula": "(169148 / 383285) * 100",
    "expected_citations": [
      {
        "page": 32,
        "table": "Consolidated Statements of Operations",
        "value": "169148"
      },
      {
        "page": 32,
        "table": "Consolidated Statements of Operations",
        "value": "383285"
      }
    ],
    "negative_test": false
  },
  {
    "id": "eval_042",
    "document": "Tesla_FY22_10K.pdf",
    "category": "not_in_doc",
    "question": "What were the marketing expenses specifically for Cybertruck in 2022?",
    "ground_truth_answer": "Not found in the document",
    "negative_test": true // Tests agent's refusal to hallucinate
  }
]
```

### Breakdown of the 100+ Benchmark Questions:
1. **Direct Fact Lookup (30 questions):** Clear numbers stated explicitly on Income Statement, Balance Sheet, or Cash Flow.
2. **Deterministic Calculations (30 questions):** YoY growth, operating margin, current ratio, effective tax rate.
3. **Multi-Year / Cross-Report Comparison (20 questions):** Comparing metric trends across 2-3 fiscal years.
4. **Complex / Scanned Tables (10 questions):** Data embedded in footnotes, dense multi-row disclaimers, or OCR scans.
5. **Negative / Unanswerable (15 questions):** Specific metrics not disclosed in the filing. The agent must strictly say *"Not found in the document"*.

---

## 2. Evaluation Metrics

| Metric | Target | Definition |
| :--- | :--- | :--- |
| **Retrieval Hit Rate** | $\ge 90\%$ | Percentage of questions where the ground-truth page/chunk is present in top-k retrieved contexts. |
| **Answer Accuracy** | $\ge 85\%$ | Exact match or within numeric tolerance ($\pm 0.1\%$) of the ground-truth value. |
| **Citation Precision** | $\ge 95\%$ | Percentage of cited page numbers and tables that accurately contain the claimed numbers. |
| **Hallucination / False Positive Rate** | $< 2\%$ | Percentage of negative questions where the agent invented a number instead of saying "not found". |
| **Calculation Accuracy** | $100\%$ | Tool execution accuracy when formulas are invoked. |

---

## 3. Evaluation Runner & Regression Guard

### Execution:
A single CLI script runs the entire eval suite and generates a structured summary:
```bash
python -m app.ai.evals.run_evals --dataset eval_dataset.json --report report.json
```

### Automatic Regression Check (CI/CD / Pre-commit):
`regression_check.py` compares current results against `baseline_results.json`:
- Fails with exit code `1` if overall accuracy drops by $> 2\%$.
- Fails if retrieval hit rate drops below $90\%$.
- Generates a breakdown of failures by category (`scanned_table`, `multi_year`, etc.) so regressions are immediately localized.

---

## 4. Observability & Cost Tracking (Langfuse / LangSmith)
For every eval query and live user query, log:
- **Total latency** (retrieval time vs LLM reasoning time vs tool execution time).
- **Prompt and completion tokens** + estimated dollar cost.
- **Tool calls executed** (with input expressions and output values).
