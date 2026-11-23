

LedgerLens: full feature list

1. Documents

Upload annual reports and filings (PDF), or pick from a small library of sample reports
Handles text pages, tables, charts, and scanned pages (OCR)
Processing runs in the background with a progress status
Each user sees only their own documents

2. Asking questions

Chat interface with streaming answers
Questions across one report or several (for example, comparing 3 years)
Follow-up questions that remember the conversation
Says "not found in the document" instead of guessing

3. Answers you can verify

Every number links to its source: page, table, and cell
Click a citation to see the original page highlighted
Calculations (margins, growth, ratios) run in code, and the formula is shown
A confidence indicator on each answer

4. Self-checking

Cross-checks numbers across sections and years
Flags inconsistencies, such as totals that don't match, unit mismatches, or restated figures

5. Quality and evals

Test set of 100+ questions with known answers
One command or button reruns the eval and shows accuracy and retrieval hit rate
Failure breakdown by type (scanned tables, multi-year, "not in document")
Automatic regression check, so changes that lower the score are caught
Dashboard with score history

6. Reliability and cost

Retries, timeouts, and clean error messages
Caching of repeated questions
Cost and latency logged for every request
Admin view: cost per question, slow queries, failed runs

7. Security

Login and per-user data separation
Protection against prompt injection in uploaded documents
API keys kept out of code

8. Product basics

Thumbs up/down and "report wrong answer" on each response
Export an answer as a short summary with citations
Disclaimer: not financial advice, check the source page

9. Engineering

Dockerized, deployed live with a public link
README with architecture diagram, 5 key design decisions, eval results, and failure analysis
Short demo video

Build order and cut line

Core (must ship): sections 1, 2, 3 (citations and calculations), 5 (evals), and the deploy part of 9
Strong additions: section 4, section 6, and section 7
Stretch (only if time allows): the clickable highlighted page, export, admin dashboard, and multi-document comparison