
#	Phase	What to do (simple)	What to document
1	Find failures	Read 50 outputs, list how it breaks	failure_analysis.md: 5-10 failure types with 2 real examples each
2	Test set	Make 100+ questions with correct answers	dataset.md: how you built it, what it covers, dev/test split
3	Graders	Write checks for relevance, faithfulness, correctness, coherence	graders.md: each rubric and judge prompt
4	Validate judges	Label 50 examples yourself, compare with the judge	judge_validation.md: agreement numbers, what you fixed
5	Run and diagnose	Score the system, read the worst 20 outputs	results_v1.md: scores table, root causes
6	Regression tests	Auto-run evals on every change with pass thresholds	GitHub Actions file plus a short ci.md
7	Monitor	Add Langfuse/LangSmith tracing	Screenshots of traces and a dashboard
8	Close the loop	Add production failures to the test set	changelog.md: before/after scores
9	Safety	Test prompt injection, PII leaks, out-of-scope	safety_report.md: attacks tried, results