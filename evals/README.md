
leave-policy-bot/
├── README.md                      ← final results + links (written last)
├── .gitignore
├── .env                           ← API keys (never upload)
├── CHANGELOG.md                   ← Step 5, 8: score after each change
├── LIMITATIONS.md                 ← written at the end
│
├── backend/                       ← the RAG app you are evaluating
│   ├── main.py
│   ├── rag.py                     ← Step 7 tracing is added here
│   ├── requirements.txt
│   └── data/                      ← HR PDF
│
├── frontend/
│   └── app.py                     ← demo UI only
│
├── evals/
│   ├── failure_log.csv            ← STEP 1
│   ├── dataset/
│   │   ├── generate_questions.py  ← STEP 2
│   │   ├── dev_set.json           ← STEP 2
│   │   └── test_set.json          ← STEP 2 (frozen)
│   ├── judges/
│   │   ├── relevance.txt          ← STEP 3
│   │   ├── faithfulness.txt       ← STEP 3
│   │   ├── correctness.txt        ← STEP 3
│   │   └── coherence.txt          ← STEP 3
│   ├── judge_validation/
│   │   ├── human_labels.csv       ← STEP 4
│   │   └── compare.py             ← STEP 4
│   ├── run_evals.py               ← STEP 5 and 6
│   ├── safety_tests.py            ← STEP 9
│   └── results/                   ← STEP 5: score files per version
│
├── .github/
│   └── workflows/
│       └── eval.yml               ← STEP 6
│
└── notes/                         ← documentation, one file per step
    ├── 01_failure_analysis.md
    ├── 02_dataset.md
    ├── 03_graders.md
    ├── 04_judge_validation.md
    ├── 05_results.md
    ├── 06_ci.md
    ├── 07_monitoring.md
    ├── 08_feedback_loop.md
    ├── 09_safety_report.md
    └── images/                    ← screenshots (Langfuse, CI runs)

