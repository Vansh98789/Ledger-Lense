Hand-code vs AI: the split

Rule: you design and write the parts that make the project unique. AI writes the parts nobody will ask you about. Roughly 40% you, 60% AI-assisted.

Part	Who writes it	Why
Architecture, data flow, feature order	You, on paper	This is what interviewers ask about
Chunking and table-aware splitting	You write, AI critiques	Core to retrieval quality
Retrieval logic (hybrid search, reranking)	You write the first version, AI helps improve	You must explain why it works
Calculation tool (the math runs in code)	You	This is the "verifiable" part
Verification and cross-check logic	You	Your signature feature
Eval set and scoring script	You write the questions and answers. AI can help write the runner	The test set must be yours
Error analysis and fixes	You	The part that proves you understand
FastAPI boilerplate, DB setup, config	AI	Boilerplate
Frontend (React UI, styling, streaming)	AI, you review	Quick to check visually
Dockerfile, deployment config	AI, you read it	Understand, but don't memorize
Tests, README polish	AI drafts, you edit and add real numbers	Keep your own voice

How to use AI on the parts you write: write the first version yourself, then ask the AI "what's weak here and why?" Read every diff, and commit after each feature.

What to focus on first: evals and a thin working version, not the UI

Most people start with the interface and finish with a pretty demo that doesn't