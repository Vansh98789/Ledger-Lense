import sys
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from backend/ folder
load_dotenv(Path(__file__).parent / ".env")

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DEBUG_DIR = BASE_DIR / "debug"
DEBUG_DIR.mkdir(exist_ok=True)

# ── Args ───────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    print("Usage: python test_pipeline.py <filename.pdf>")
    print(f"Place your PDF inside: {DATA_DIR}")
    sys.exit(1)

pdf_path = DATA_DIR / sys.argv[1]
if not pdf_path.exists():
    print(f"❌  File not found: {pdf_path}")
    sys.exit(1)

# ── Import pipeline ────────────────────────────────────────────────────────
from app.extract_data import extract_data
from app.chunking import chunk_document_items

# ── Run extraction ─────────────────────────────────────────────────────────
print(f"\n📄  PDF       : {pdf_path.name}")
print("🔍  Running extraction...")

pdf_bytes = pdf_path.read_bytes()
extracted_items = extract_data(
    pdf_source=pdf_bytes,
    analyze_vlm=False,
)

print(f"✅  Extracted : {len(extracted_items)} items")

# Type breakdown
from collections import Counter

type_counts = Counter(item["type"] for item in extracted_items)
for t, count in sorted(type_counts.items()):
    print(f"     {t:<15} {count}")

# ── Run chunking ───────────────────────────────────────────────────────────
print("\n✂️   Running chunking...")

chunks = chunk_document_items(
    extracted_items=extracted_items,
    pdf_source=pdf_bytes,  # needed for scanned VLM rescan fallback
)

print(f"✅  Chunks    : {len(chunks)} total")

chunk_type_counts = Counter(c.get("type", "unknown") for c in chunks)
for t, count in sorted(chunk_type_counts.items()):
    print(f"     {t:<15} {count}")

# ── Save output ────────────────────────────────────────────────────────────
output = {
    "pdf": pdf_path.name,
    "extracted_item_count": len(extracted_items),
    "chunk_count": len(chunks),
    "extracted_items": extracted_items,
    "chunks": chunks,
}

out_file = DEBUG_DIR / "debug_output.json"
with open(out_file, "w", encoding="utf-8") as f:
    json.dump(output, f, indent=2, ensure_ascii=False, default=str)

print(f"\n💾  Saved to  : {out_file}")
print("Done.\n")
