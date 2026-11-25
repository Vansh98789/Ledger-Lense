# Rules — What You Write vs What AI Writes

**Principle:** You write the parts that make this project yours. AI writes the boilerplate. Roughly 40% you, 60% AI-assisted.

---

## Ownership Split

| Part | Owner | Why |
|---|---|---|
| Architecture, data flow, feature order | You | Interviewers ask about this |
| Chunking & table-aware splitting | You write, AI critiques | Core to retrieval quality |
| Retrieval logic (hybrid search, reranking) | You write first version, AI improves | You must explain why it works |
| Calculation tool (math runs in code) | You | The "verifiable" differentiator |
| Verification & cross-check logic | You | Your signature feature |
| Eval set & scoring script | You write questions/answers, AI writes runner | Test set must be yours |
| Error analysis & fixes | You | Proves you understand the system |
| FastAPI boilerplate, DB setup, config | AI | Nobody asks about this |
| Frontend (React, styling, streaming) | AI, you review | Quick to check visually |
| Dockerfile, deployment config | AI, you read it | Understand, don't memorize |
| Tests, README polish | AI drafts, you edit | Keep your voice |

---

## How to Use AI on Parts You Write

Write the first version yourself, then ask: **"What's weak here and why?"**
Read every diff. Commit after each feature.

---

## Priority Order

**Ship this first:** evals + a thin working version end-to-end. Not the UI.

Most people build the interface first and end up with a pretty demo that breaks on real questions. Evals first means you know when it actually works.
