"""
test_pipeline.py

Usage:
    cd backend
    .venv\Scripts\python.exe test_pipeline.py <filename.pdf> [question]
Examples:
    .venv\Scripts\python.exe test_pipeline.py apple_fy23.pdf "What was total revenue in 2023?"
"""

import sys
import json
from pathlib import Path
from collections import Counter
from dotenv import load_dotenv

# Load .env FIRST before importing app.*
load_dotenv(Path(__file__).parent / ".env")

# ── Paths ───────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEBUG_DIR = BASE_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)

# ── Args ────────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print("Usage: python test_pipeline.py <filename.pdf> [question]")
    print(f"Place your PDF inside: {DATA_DIR}")
    sys.exit(1)

pdf_path = DATA_DIR / sys.argv[1]
if not pdf_path.exists():
    print(f"❌  File not found: {pdf_path}")
    sys.exit(1)

TEST_QUESTION = (
    " ".join(sys.argv[2:])
    if len(sys.argv) > 2
    else "What is this document about? Summarize key financial numbers."
)
TEST_DOC_ID = "test_doc"
TEST_USER_ID = "test_user"
TEST_COL = "test_pipeline_col"

# ── Imports ─────────────────────────────────────────────────────────────────
from app.extract_data import extract_data
from app.clean_data import clean_extracted_items
from app.chunking import chunk_document_items
from app.embedding import embed_texts
from app.db.chroma_intergration import upsert_chunks, delete_document_chunks
from app.retreival import retrieve, answer_question

# ════════════════════════════════════════════════════════════════════════════
# STEP 1: EXTRACTION
# ════════════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
print(f"📄  PDF       : {pdf_path.name}")
print(f"{'=' * 60}")

pdf_bytes = pdf_path.read_bytes()

print("\n🔍  [1/5] Extracting...")
extracted_items = extract_data(pdf_source=pdf_bytes, analyze_vlm=False)
print(f"     Raw items  : {len(extracted_items)}")
for t, n in sorted(Counter(i["type"] for i in extracted_items).items()):
    print(f"       {t:<16} {n}")

# ════════════════════════════════════════════════════════════════════════════
# STEP 2: CLEANING
# ════════════════════════════════════════════════════════════════════════════
print("\n🧹  [2/5] Cleaning (dedup + overlap filter)...")
cleaned_items = clean_extracted_items(extracted_items)
dropped = len(extracted_items) - len(cleaned_items)
print(f"     Cleaned    : {len(cleaned_items)} items  ({dropped} dropped)")

# ════════════════════════════════════════════════════════════════════════════
# STEP 3: CHUNKING
# ════════════════════════════════════════════════════════════════════════════
print("\n✂️   [3/5] Chunking...")
chunks = chunk_document_items(extracted_items=cleaned_items, pdf_source=pdf_bytes)
chunks = [c for c in chunks if c.get("content", "").strip()]
print(f"     Chunks     : {len(chunks)}")
for t, n in sorted(Counter(c.get("type", "unknown") for c in chunks).items()):
    print(f"       {t:<16} {n}")

# ════════════════════════════════════════════════════════════════════════════
# STEP 4: EMBED + UPSERT
# ════════════════════════════════════════════════════════════════════════════
print("\n🔢  [4/5] Embedding + upserting to Chroma...")
embeddings = embed_texts([c["content"] for c in chunks])
upserted = upsert_chunks(
    chunks,
    embeddings,
    doc_id=TEST_DOC_ID,
    user_id=TEST_USER_ID,
    collection_name=TEST_COL,
)
print(f"     Upserted   : {upserted} vectors")

# ════════════════════════════════════════════════════════════════════════════
# STEP 5: RETRIEVAL + LLM ANSWER
# ════════════════════════════════════════════════════════════════════════════
print(f"\n🤖  [5/5] Q&A...")
print(f"     Question   : {TEST_QUESTION}")

top_chunks = retrieve(
    query=TEST_QUESTION,
    user_id=TEST_USER_ID,
    doc_ids=[TEST_DOC_ID],
    collection_name=TEST_COL,
)
print(f"\n     Top chunks retrieved ({len(top_chunks)}):")
for i, c in enumerate(top_chunks):
    print(
        f"       [{i}] type={c.get('chunk_type', '?')} page={c.get('page_number', '?')} rerank={c.get('rerank_score', '?')} src={c.get('retrieval_sources', '?')}"
    )

result = answer_question(
    query=TEST_QUESTION,
    user_id=TEST_USER_ID,
    doc_ids=[TEST_DOC_ID],
    collection_name=TEST_COL,
)

print(f"\n     Confidence : {result['confidence']}")
print(f"     Citations  : {len(result['citations'])}")
print(f"\n     Answer:\n     {result['answer']}")

# ════════════════════════════════════════════════════════════════════════════
# CLEANUP + SAVE
# ════════════════════════════════════════════════════════════════════════════
delete_document_chunks(TEST_DOC_ID, TEST_USER_ID, collection_name=TEST_COL)

output = {
    "pdf": pdf_path.name,
    "question": TEST_QUESTION,
    "extracted_count": len(extracted_items),
    "cleaned_count": len(cleaned_items),
    "chunk_count": len(chunks),
    "upserted_count": upserted,
    "top_chunks": top_chunks,
    "answer": result["answer"],
    "confidence": result["confidence"],
    "citations": result["citations"],
}
out_file = DEBUG_DIR / "debug_output.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\n💾  Saved to  : {out_file}")
print(f"{'=' * 60}\n")
