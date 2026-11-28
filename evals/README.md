# LedgerLens Evaluation Suite

Comprehensive 9-step evaluation pipeline for LedgerLens's financial RAG system, measuring retrieval accuracy, answer correctness, and factual faithfulness against SEC-style corporate disclosures (Tesla Q3 2024 Update).

---

## 📊 Pipeline Benchmark Results

| Metric | Target | Baseline | **Current Best (tuned_v3)** | Status |
|---|---|---|---|---|
| **Retrieval Hit@5** | ≥ 85.0% | 52.0% | **98.0%** (49/50) | ✅ PASSED |
| **Retrieval MRR** | — | 0.285 | **0.786** | ✅ PASSED |
| **Answer Correctness** | ≥ 85.0% | 48.0% | **96.0%** (24/25) | ✅ PASSED |
| **Answer Faithfulness** | ≥ 85.0% | 56.0% | **88.0%** (22/25) | ✅ PASSED |

---

## 📁 Evaluation Structure

```text
evals/
├── data/
│   └── TSLA-Q3-2024-Update.pdf          # 32-page benchmark financial PDF
├── step_1_failure_analysis/
│   ├── initial_50_questions.json        # 50 exploratory probe queries
│   ├── run_discovery.py                 # Probe runner across baseline pipeline
│   ├── raw_outputs.json                 # Raw system responses
│   └── failure_log.csv                  # Cataloged failure modes & root causes
├── step_2_dataset/
│   ├── dev_set.json                     # 50 questions for tuning & optimization
│   └── test_set.json                    # 50 frozen holdout questions (no tuning)
├── step_3_graders/
│   ├── grader_engine.py                 # Retrieval math + LLM judge execution engine
│   ├── rubrics.md                       # Evaluation scoring definitions
│   └── prompts/
│       ├── correctness.txt              # Strict precision judge rubric
│       ├── faithfulness.txt             # Hallucination detector rubric
│       └── relevance.txt                # Retrieval relevance judge rubric
├── step_4_judge_validation/
│   ├── compare.py                       # Human vs LLM judge agreement runner
│   ├── human_labels.csv                 # Human ground-truth verdicts
│   └── judge_comparison_results.json    # Agreement output (Achieved 88.0% agreement)
├── step_5_results/
│   ├── run_evals.py                     # Master evaluation harness (with --resume support)
│   ├── changelog.md                     # Iteration log tracking every tuned run
│   ├── baseline.json                    # Locked baseline score snapshot
│   └── runs/                            # Versioned run results (.json)
├── step_6_ci_guard/                     # [Next] Automated regression gatekeeper
├── step_7_monitoring/                   # [Pending] Production telemetry
├── step_8_feedback_loop/                # [Pending] Failure capture system
└── step_9_safety/                       # [Pending] Prompt injection & adversarial guardrails
```

---

## 🚀 Quickstart: Running Evaluations

Run commands from the project root directory (`leadger_lense`):

### 1. Run Dev Set (Full Run)
```powershell
backend\.venv\Scripts\python.exe evals\step_5_results\run_evals.py --split dev --tag tuned_v3
```

### 2. Resume an Interrupted Run
```powershell
backend\.venv\Scripts\python.exe evals\step_5_results\run_evals.py --split dev --tag tuned_v3 --resume
```

### 3. Run a Quick Sanity Check (e.g. 5 questions)
```powershell
backend\.venv\Scripts\python.exe evals\step_5_results\run_evals.py --split dev --tag test_run --limit 5
```

---

## 📝 Step-by-Step Documentation (`notes/`)

- [`notes/01_failure_analysis.md`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/notes/01_failure_analysis.md) — Discovery of the 4 core RAG failure modes.
- [`notes/02_dataset.md`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/notes/02_dataset.md) — Dataset design (50 dev / 50 test holdout split).
- [`notes/03_graders.md`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/notes/03_graders.md) — Deterministic and LLM judge grader architectures.
- [`notes/04_judge_validation.md`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/notes/04_judge_validation.md) — 88% human-judge alignment validation report.
- [`notes/05_results.md`](file:///c:/Users/Vansh%20Maheshwari/Desktop/leadger_lense/notes/05_results.md) — Tuning results, root causes, and before/after comparisons.
