# AGENT QUERY & QUESTION ANSWERING ARCHITECTURE
===================================================

## Overview
LedgerLens answers complex financial questions across single reports or multiple filings. It must never hallucinate financial figures, must perform calculations using deterministic code execution, and must provide verifiable citations down to the exact cell or paragraph bounding box.

---

## 1. End-to-End Agent Lifecycle

```text
[User Prompt]
      │
      ▼
1. Query Contextualizer & Intent Classifier
   ├── Resolves chat history & pronouns (e.g. "What was it in 2022?" -> "What was Apple's R&D expense in 2022?")
   └── Classifies intent:
         ├── Direct Fact Lookup (e.g. "What was FY23 Net Revenue?")
         ├── Financial Calculation (e.g. "Calculate the Operating Margin for 2023")
         ├── Multi-Period / Cross-Document Comparison (e.g. "Compare revenue growth from 2021 to 2023")
         └── Out of Scope / General Conversational
      │
      ▼
2. Hybrid Retrieval Engine (chroma db + Full-Text Search)
   |__ BM25  based retrieval
   ├── Multi-tenant query: WHERE user_id = :user_id AND doc_id IN (:doc_ids)
   ├── Vector Similarity Search: Cosine distance on chunk embeddings
   ├── Lexical / Keyword Filter: Exact match for financial terms, item headers, and year numbers
   └── Top-K Chunks returned with page numbers and bounding box coordinates
      │
      ▼
3. Agent Reasoning & Tool Invocation
   ├── Document Inspector Tool: Read specific table cells or adjacent paragraphs
   ├── Calculator Tool: Runs mathematical expressions in a deterministic Python sandbox
   └── Cross-Check Tool: Compares numbers across different sections (e.g. Net Income in Income Statement vs Cash Flow Statement)
      │
      ▼
4. Grounding & Hallucination Guardrail
   ├── Fact-Check Step: Every numeric entity in the draft answer is matched against retrieved chunks
   ├── If grounded: Proceed to stream output
   └── If ungrounded or absent: Force exact response -> "Not found in the document"
      │
      ▼
5. Structured Output & Streaming Response
   ├── Streams answer markdown to the frontend
   └── Appends structured metadata (Citations, Calculation formulas, Confidence indicator)
```

---

## 2. Tools Available to the Agent

### Tool 1: `retrieval_tool`
- **Purpose:** Fetches relevant context chunks from chroma DB using hybrid search.
- **Inputs:** `query` (str), `doc_ids` (List[str]), `page_hint` (Optional[int]).
- **Outputs:** List of chunks containing `content`, `page_number`, `bbox`, and `table_metadata`.

### Tool 2: `calculator_tool` (Deterministic Math)
- **Rule:** The LLM is **strictly forbidden from doing arithmetic mentally**.
- **Purpose:** Executes financial formulas (e.g., Growth Rate, Gross Margin, Current Ratio) using Python / `numexpr` in an isolated sandbox.
- **Inputs:** `expression` (str) e.g., `(383285 - 394328) / 394328 * 100`, `variables` (dict).
- **Outputs:** Exact computed value and the human-readable formula to display to the user.

### Tool 3: `table_cell_lookup_tool`
- **Purpose:** Queries specific table cells by row label and year/column header (e.g., Row="Operating Income", Col="2023").
- **Outputs:** Cell raw value, unit (e.g. in millions), table name, page number, and bounding box.

---

## 3. Strict Verification & Self-Checking Guardrails

Before emitting the final answer:
1. **Source Grounding Verification:**
   - Every number cited (e.g., `"$383.29B"`) must exist in the retrieved source text.
   - If the agent deduces or estimates a number not explicitly in the text or calculated via the tool, the answer is rejected.
2. **"Not Found" Fallback:**
   - If retrieved context does not contain sufficient information to answer truthfully, the agent responds with:
     > *"Not found in the document."*
   - It will **never** guess or hallucinate financial values.
3. **Cross-Checking Inconsistencies:**
   - When answering multi-period or multi-statement questions, the agent flags discrepancies (e.g., restated numbers in subsequent 10-K filings, unit mismatches between thousands vs millions).

---

## 4. Response Payload Schema (JSON / SSE Stream)

```json
{
  "answer": "Apple's Gross Margin for FY2023 was 44.13%, calculated as Gross Profit ($169,148 million) divided by Total Net Sales ($383,285 million).",
  "confidence": "HIGH", // HIGH, MEDIUM, LOW, or NOT_FOUND
  "calculations": [
    {
      "metric": "Gross Margin",
      "formula": "(169148 / 383285) * 100",
      "result": 44.1319,
      "formatted_result": "44.13%"
    }
  ],
  "citations": [
    {
      "doc_id": "8b52df39-4d64-4e2b-bb23-1d02c89f518e",
      "page_number": 32,
      "table_id": "Consolidated_Statements_of_Operations",
      "cell_ref": "Row: Total net sales, Col: 2023",
      "value_cited": "$383,285",
      "bbox": [54.0, 180.2, 490.5, 195.0]
    },
    {
      "doc_id": "8b52df39-4d64-4e2b-bb23-1d02c89f518e",
      "page_number": 32,
      "table_id": "Consolidated_Statements_of_Operations",
      "cell_ref": "Row: Gross margin, Col: 2023",
      "value_cited": "$169,148",
      "bbox": [54.0, 240.0, 490.5, 255.4]
    }
  ]
}
```
