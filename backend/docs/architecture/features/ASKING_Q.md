# Question Answering

User asks a question → agent retrieves relevant chunks → runs tools → verifies → streams answer with citations.

---

## Flow

```
User Question
    │
    ▼
1. Query Rewriter
   - Resolves pronouns / follow-ups using chat history
   - Classifies intent: Direct Lookup | Calculation | Multi-Year Comparison | Out of Scope

    │
    ▼
2. Hybrid Retrieval (Neon pgvector)
   - Scoped by user_id + selected doc_id(s)
   - Vector cosine similarity + keyword filter (metric names, years, tickers)
   - Returns top-k chunks with page_number, bbox, content, metadata

    │
    ▼
3. Tool Execution
   - calculator_tool   → deterministic Python sandbox for math (margins, ratios, growth %)
   - table_cell_lookup → fetch specific row+col value from a stored table chunk

    │
    ▼
4. Hallucination Guardrail
   - Every number in the draft answer must exist in a retrieved chunk
   - If ungrounded → response is replaced with "Not found in the document"
   - Flags unit mismatches (thousands vs millions) and restated figures

    │
    ▼
5. Streaming Response
   - Markdown answer streamed token-by-token (SSE)
   - Citation JSON emitted alongside: page, bbox, table_id, cell_ref, value
```

---

## Tools

**`calculator_tool`** — LLM never does mental math. Expressions like `(169148 / 383285) * 100` run in a Python sandbox. Returns: formula + result.

**`table_cell_lookup`** — Query by `(row_label, col_header)` → returns raw value, unit, page, bbox.

---

## Response Schema

```json
{
  "answer": "Apple's Gross Margin for FY2023 was 44.13%.",
  "confidence": "HIGH",
  "calculations": [
    {
      "metric": "Gross Margin",
      "formula": "(169148 / 383285) * 100",
      "result": 44.1319,
      "formatted": "44.13%"
    }
  ],
  "citations": [
    {
      "doc_id": "...",
      "page_number": 32,
      "table_id": "Consolidated_Statements_of_Operations",
      "cell_ref": "Row: Total net sales, Col: 2023",
      "value": "$383,285",
      "bbox": [54.0, 180.2, 490.5, 195.0]
    }
  ]
}
```

`confidence`: `HIGH` | `MEDIUM` | `LOW` | `NOT_FOUND`
