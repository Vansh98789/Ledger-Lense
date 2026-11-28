import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

# Ensure backend modules can be imported
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv

load_dotenv(BACKEND_DIR / ".env")

from app.db.chroma_intergration import get_collection
from app.ingestion import ingest_document
from app.retrieval import answer_question

PDF_FILENAME = "TSLA-Q3-2024-Update.pdf"
PDF_PATH = REPO_ROOT / "evals" / "data" / PDF_FILENAME
DOC_ID = "eval_tsla_q3_2024"
USER_ID = "eval_tester"

QUESTIONS_FILE = Path(__file__).parent / "initial_50_questions.json"
OUTPUT_RAW_FILE = Path(__file__).parent / "raw_outputs.json"
FAILURE_LOG_CSV = Path(__file__).parent / "failure_log.csv"


# check and do ingestion -->
def check_and_ingest():
    if not PDF_PATH.exists():
        raise FileNotFoundError(f"Benchmark PDF not found at: {PDF_PATH}")

    collection = get_collection()
    existing = collection.get(where={"doc_id": DOC_ID}, limit=1)
    # ingestion already exists-->
    if existing and existing.get("ids"):
        print(f"[OK] Document '{DOC_ID}' is already ingested in ChromaDB.")
        return

    print(f"[INGEST] Ingesting '{PDF_FILENAME}' into ChromaDB (doc_id={DOC_ID})...")
    start = time.time()
    result = ingest_document(
        pdf_source=str(PDF_PATH),
        doc_id=DOC_ID,
        user_id=USER_ID,
        analyze_vlm=False,
    )
    elapsed = time.time() - start
    print(
        f"[INGEST DONE] Upserted {result.get('upserted_count', 0)} chunks in {elapsed:.1f}s.\n"
    )


def normalize_text(text: str) -> str:
    return text.lower().replace(",", "").replace("$", "").replace("%", "").strip()


def evaluate_retrieval(
    retrieved_chunks: List[Dict[str, Any]], expected_page: Any
) -> bool:
    if expected_page is None:
        return len(retrieved_chunks) == 0  # to handle the normal conversation case

    expected_pages = (
        [expected_page] if isinstance(expected_page, int) else list(expected_page)
    )

    for chunk in retrieved_chunks:
        page = chunk.get("page_number")
        if page in expected_pages:
            return True
    return False


def evaluate_generation_rules(
    answer: str, expected_gen: Dict[str, Any]
) -> Dict[str, bool]:
    norm_answer = normalize_text(answer)

    must_include = expected_gen.get("must_include", [])
    must_not_include = expected_gen.get("must_not_include", [])

    include_pass = True
    for item in must_include:
        norm_item = normalize_text(item)
        # Check if key tokens are present
        tokens = [t for t in norm_item.split() if len(t) > 2]
        if tokens and not any(t in norm_answer for t in tokens):
            include_pass = False
            break

    not_include_pass = True
    for item in must_not_include:
        norm_item = normalize_text(item)
        if norm_item and norm_item in norm_answer:
            not_include_pass = False
            break

    return {
        "must_include_passed": include_pass,
        "must_not_include_passed": not_include_pass,
    }


def run_discovery():
    check_and_ingest()

    with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)

    tests: List[Dict[str, Any]] = []
    # Support both partitioned dictionary and flat list
    if isinstance(data, dict):
        retrieval_tests = data.get("retrieval_tests", [])
        generation_tests = data.get("generation_tests", [])
        for t in retrieval_tests:
            t["test_type"] = "retrieval_focus"
            tests.append(t)
        for t in generation_tests:
            t["test_type"] = "generation_focus"
            tests.append(t)
    elif isinstance(data, list):
        tests = data

    print("\n=======================================================")
    print(f"  RUNNING STEP 1 FAILURE DISCOVERY ({len(tests)} TESTS)")
    print("=======================================================\n")

    results = []
    failures = []

    for idx, test in enumerate(tests, 1):
        test_id = test.get("id", f"TC_{idx:03d}")
        question = test.get("question", "")
        test_type = test.get("test_type", "general")
        expected_ret = test.get("expected_retrieval", {})
        expected_gen = test.get("expected_generation", {})
        expected_page = expected_ret.get("page")
        ground_truth = expected_gen.get("ground_truth_answer", "")

        t0 = time.time()
        try:
            res = answer_question(
                query=question,
                user_id=USER_ID,
                doc_ids=[DOC_ID],
                top_k=5,
            )
            elapsed = time.time() - t0
            answer = res.get("answer", "")
            chunks = res.get("retrieved_chunks", [])
            citations = res.get("citations", [])
        except Exception as e:
            elapsed = time.time() - t0
            answer = f"ERROR: {str(e)}"
            chunks = []
            citations = []

        # Evaluate checks
        retrieval_hit = evaluate_retrieval(chunks, expected_page)
        gen_rules = evaluate_generation_rules(answer, expected_gen)

        retrieved_pages = [c.get("page_number") for c in chunks]

        status_ret = "PASS" if retrieval_hit else "FAIL"
        status_inc = "PASS" if gen_rules["must_include_passed"] else "FLAGGED"

        # Record output
        record = {
            "id": test_id,
            "test_type": test_type,
            "question": question,
            "expected_page": expected_page,
            "ground_truth": ground_truth,
            "retrieval_hit": retrieval_hit,
            "retrieved_pages": retrieved_pages,
            "must_include_passed": gen_rules["must_include_passed"],
            "must_not_include_passed": gen_rules["must_not_include_passed"],
            "generated_answer": answer,
            "retrieved_chunk_count": len(chunks),
            "citations": citations,
            "latency_seconds": round(elapsed, 2),
            "retrieved_chunks_preview": [
                {
                    "page": c.get("page_number"),
                    "type": c.get("chunk_type"),
                    "preview": c.get("content", "")[:200],
                }
                for c in chunks
            ],
        }
        results.append(record)

        print(
            f"[{idx:02d}/{len(tests)}] {test_id} | Ret: {status_ret:<4} (exp p.{expected_page}, got {retrieved_pages}) | "
            f"GenCheck: {status_inc:<7} | {elapsed:.2f}s | {question[:45]}..."
        )

        # Flag for human inspection if retrieval failed or rules flagged
        if (
            not retrieval_hit
            or not gen_rules["must_include_passed"]
            or not gen_rules["must_not_include_passed"]
        ):
            failures.append(
                {
                    "id": test_id,
                    "test_type": test_type,
                    "question": question,
                    "expected_page": expected_page,
                    "retrieved_pages": str(retrieved_pages),
                    "generated_answer": answer.replace("\n", " ")[:300],
                    "ground_truth": ground_truth,
                    "retrieval_hit": retrieval_hit,
                    "failure_type": "RETRIEVAL_MISS"
                    if not retrieval_hit
                    else "GENERATION_INACCURACY",
                    "root_cause": "To be verified by human reviewer in Step 1",
                }
            )

    # 1. Save full granular JSON outputs
    with open(OUTPUT_RAW_FILE, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)

    # 2. Save failure log template CSV
    import csv

    with open(FAILURE_LOG_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "id",
                "test_type",
                "question",
                "expected_page",
                "retrieved_pages",
                "generated_answer",
                "ground_truth",
                "retrieval_hit",
                "failure_type",
                "root_cause",
            ],
        )
        writer.writeheader()
        for fail in failures:
            writer.writerow(fail)

    ret_hits = sum(1 for r in results if r["retrieval_hit"])
    print("\n=======================================================")
    print("  STEP 1 DISCOVERY RUN COMPLETE")
    print("=======================================================")
    print(f"Total Tests:        {len(tests)}")
    print(
        f"Retrieval Hits:     {ret_hits} / {len(tests)} ({ret_hits / len(tests) * 100:.1f}%)"
    )
    print(f"Flagged for Review: {len(failures)} cases written to:")
    print(f"  -> {FAILURE_LOG_CSV}")
    print("Full details saved to:")
    print(f"  -> {OUTPUT_RAW_FILE}")


if __name__ == "__main__":
    run_discovery()
