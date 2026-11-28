# Step 5 — Eval Iteration Log

> Tune on `dev_set.json` only. Write `notes/05_results.md` once all metrics hit **≥ 85%**.

## Targets
| Metric | Target | Baseline | Best So Far |
|---|---|---|---|
| Retrieval Hit@5 | ≥ 85% | 52.0% | 52.0% |
| Answer Correctness | ≥ 85% | 48.0% | 48.0% |
| Answer Faithfulness | ≥ 85% | 56.0% | 56.0% |

---

## baseline — 2026-11-28
- **Tag:** `baseline`
- **Changed:** Nothing. First run.
- **Scores:** Hit@5 52% | Correctness 48% | Faithfulness 56% | MRR 0.285
- **File:** `runs/run_dev_baseline_20261128_133427.json`

---

<!-- TEMPLATE — copy below for each new run

## tuned_v1 — YYYY-MM-DD
- **Tag:** `tuned_v1`
- **Changed:** <file> — <what you did>
- **Scores:** Hit@5 ?% | Correctness ?% | Faithfulness ?% | MRR ?.???
- **Delta:** Hit@5 +?% | Correctness +?% | Faithfulness +?%
- **File:** `runs/run_dev_tuned_v1_*.json`

-->
