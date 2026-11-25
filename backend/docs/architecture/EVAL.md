# Eval Process (How to Run & Improve)

Ordered steps to build and maintain a trustworthy eval loop.

| # | Phase | What to do | Output |
|---|---|---|---|
| 1 | Find failures | Read 50 real outputs, list how the system breaks | `failure_analysis.md`: 5–10 failure types with 2 real examples each |
| 2 | Build test set | Write 100+ questions with correct answers | `eval_dataset.json` covering all categories |
| 3 | Write graders | Checks for relevance, faithfulness, correctness, coherence | `graders.md`: rubric + judge prompt per dimension |
| 4 | Validate judges | Label 50 examples yourself, compare with the judge | `judge_validation.md`: agreement %, what you fixed |
| 5 | Run & diagnose | Score the system, read the worst 20 outputs | `results_v1.md`: scores table + root causes |
| 6 | Regression guard | Auto-run evals on every change with pass thresholds | GitHub Actions file + `ci.md` |
| 7 | Monitor | Add Langfuse/LangSmith tracing | Trace screenshots + latency/cost dashboard |
| 8 | Close the loop | Add production failures back into the test set | `changelog.md`: before/after scores |
| 9 | Safety | Test prompt injection, PII leaks, out-of-scope questions | `safety_report.md`: attacks tried + results |
