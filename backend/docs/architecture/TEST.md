# Evals & Testing

---

## Eval Dataset (`eval_dataset.json`)

100+ questions with known answers. Categories:

| Category | Count | Description |
|---|---|---|
| `direct_lookup` | 30 | Explicit numbers from Income Statement, Balance Sheet, Cash Flow |
| `calculation` | 30 | YoY growth, margin, ratio — requires calculator tool |
| `multi_year` | 20 | Comparing metrics across 2–3 fiscal years |
| `scanned_table` | 10 | Data in footnotes, dense multi-row tables, OCR pages |
| `not_in_doc` | 15 | Questions with no answer — agent must refuse, not guess |

### Entry Schema
```json
{
  "id": "eval_001",
  "document": "Apple_FY23_10K.pdf",
  "category": "calculation",
  "question": "What was Apple's gross margin percentage in FY2023?",
  "ground_truth_answer": "44.13%",
  "ground_truth_numeric": 44.13,
  "tolerance": 0.05,
  "requires_calculation": true,
  "expected_formula": "(169148 / 383285) * 100",
  "expected_citations": [
    { "page": 32, "table": "Consolidated Statements of Operations", "value": "169148" },
    { "page": 32, "table": "Consolidated Statements of Operations", "value": "383285" }
  ],
  "negative_test": false
}
```

---

## Metrics & Targets

| Metric | Target |
|---|---|
| Retrieval Hit Rate | ≥ 90% — ground-truth chunk in top-k |
| Answer Accuracy | ≥ 85% — exact match or within ±0.1% |
| Citation Precision | ≥ 95% — cited page/table actually contains the number |
| Hallucination Rate | < 2% — negative questions where agent invented a number |
| Calculation Accuracy | 100% — calculator tool must never return wrong math |

---

## Running Evals

```bash
python -m app.evals.run_evals --dataset eval_dataset.json --report report.json
```

`regression_check.py` compares output against `baseline_results.json`:
- Exits with code `1` if overall accuracy drops > 2%
- Exits with code `1` if retrieval hit rate drops below 90%
- Failure breakdown by category so regressions are localized immediately
