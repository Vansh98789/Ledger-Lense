import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

# Ensure backend and evals can be imported
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from app.db.chroma_intergration import get_collection
from app.ingestion import ingest_document
from app.retrieval import answer_question, retrieve
from evals.step_3_graders.grader_engine import (
    grade_correctness,
    grade_faithfulness,
    grade_retrieval,
)

DATA_DIR = REPO_ROOT / "evals" / "data"
DATASET_DIR = REPO_ROOT / "evals" / "step_2_dataset"
RESULTS_DIR = Path(__file__).parent
RUNS_DIR = RESULTS_DIR / "runs"

PDF_FILENAME = "TSLA-Q3-2024-Update.pdf"
PDF_PATH = DATA_DIR / PDF_FILENAME
DOC_ID = "eval_tsla_q3_2024"
USER_ID = "eval_tester"


def ensure_dirs():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)


def check_and_ingest():
    """Ensure the benchmark PDF is in ChromaDB."""
    collection = get_collection()
    existing = collection.get(where={"doc_id": DOC_ID}, limit=1)
    if existing and existing.get("ids"):
        return

    print(f"[INGEST] Ingesting {PDF_FILENAME} into ChromaDB...")
    ingest_document(
        pdf_source=str(PDF_PATH),
        doc_id=DOC_ID,
        user_id=USER_ID,
        analyze_vlm=False,
    )
    print("[INGEST DONE] Ready for evaluation.\n")


def load_dataset(split: str) -> List[Dict[str, Any]]:
    file_path = DATASET_DIR / f"{split}_set.json"
    if not file_path.exists():
        raise FileNotFoundError(f"Dataset file not found: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    tests: List[Dict[str, Any]] = []
    if isinstance(data, dict):
        ret = data.get("retrieval_tests", [])
        gen = data.get("generation_tests", [])
        for t in ret:
            t["test_stage"] = "retrieval"
            tests.append(t)
        for t in gen:
            t["test_stage"] = "generation"
            tests.append(t)
    elif isinstance(data, list):
        tests = data

    return tests


def _recount(results):
    """Recompute running counters from a partial results list."""
    retrieval_hits = 0
    total_retrieval_mrr = 0.0
    retrieval_count = 0
    correctness_passes = 0
    faithfulness_passes = 0
    generation_count = 0
    for r in results:
        if r["test_stage"] == "retrieval":
            retrieval_count += 1
            if r.get("retrieval_hit"):
                retrieval_hits += 1
            total_retrieval_mrr += r.get("reciprocal_rank", 0.0)
        else:
            retrieval_count += 1
            if r.get("retrieval_hit"):
                retrieval_hits += 1
            total_retrieval_mrr += r.get("reciprocal_rank", 0.0)
            generation_count += 1
            if r.get("correctness", {}) and r["correctness"].get("verdict") == "PASS":
                correctness_passes += 1
            if r.get("faithfulness", {}) and r["faithfulness"].get("verdict") == "PASS":
                faithfulness_passes += 1
    return retrieval_hits, total_retrieval_mrr, retrieval_count, correctness_passes, faithfulness_passes, generation_count


def run_evaluation(split: str = "dev", limit: Optional[int] = None, tag: str = "baseline", resume: bool = False):
    ensure_dirs()
    check_and_ingest()

    tests = load_dataset(split)
    if limit and limit > 0:
        tests = tests[:limit]

    # --- Resume: load partial results from latest_run.json ---
    partial_file = RUNS_DIR / "latest_run.json"
    results = []
    start_from = 0
    if resume and partial_file.exists():
        with open(partial_file, "r", encoding="utf-8") as f:
            partial = json.load(f)
        results = partial.get("results", [])
        done_ids = {r["id"] for r in results}
        start_from = len(results)
        print(f"[RESUME] Found {start_from} completed questions. Skipping to Q{start_from + 1}.\n")
        tests = [t for t in tests if t.get("id", "") not in done_ids]

    retrieval_hits, total_retrieval_mrr, retrieval_count, correctness_passes, faithfulness_passes, generation_count = _recount(results)

    print("=================================================================")
    print(f"  RUNNING EVALUATION: [{split.upper()} SET] | TAG: [{tag.upper()}] ({len(tests)} REMAINING)")
    print("=================================================================\n")

    total_start = time.time()

    for idx, test in enumerate(tests, start_from + 1):
        test_id = test.get("id", f"TC_{idx:03d}")
        question = test.get("question", "")
        test_stage = test.get("test_stage", "generation")
        expected_ret = test.get("expected_retrieval", {})
        expected_gen = test.get("expected_generation", {})
        expected_page = expected_ret.get("page")
        ground_truth = expected_gen.get("ground_truth_answer", "")
        must_include = expected_gen.get("must_include", [])
        must_not_include = expected_gen.get("must_not_include", [])

        t0 = time.time()

        # -------------------------------------------------------------
        # Case A: Retrieval-Focused Question (Blazing Fast: No Gen LLM)
        # -------------------------------------------------------------
        if test_stage == "retrieval":
            chunks = retrieve(
                query=question,
                user_id=USER_ID,
                doc_ids=[DOC_ID],
                top_k=5,
            )
            elapsed = time.time() - t0

            ret_res = grade_retrieval(chunks, expected_page)
            retrieval_hit = ret_res["hit"]
            reciprocal_rank = ret_res["reciprocal_rank"]

            retrieval_count += 1
            if retrieval_hit:
                retrieval_hits += 1
            total_retrieval_mrr += reciprocal_rank

            status = "PASS" if retrieval_hit else "FAIL"
            print(
                f"[{idx:02d}/{len(tests)}] {test_id} [RETRIEVAL] | Hit@5: {status:<4} (exp p.{expected_page}, got {ret_res['retrieved_pages']}) | "
                f"{elapsed:.2f}s | {question[:42]}..."
            )

            results.append({
                "id": test_id,
                "test_stage": test_stage,
                "question": question,
                "expected_page": expected_page,
                "retrieved_pages": ret_res["retrieved_pages"],
                "retrieval_hit": retrieval_hit,
                "reciprocal_rank": reciprocal_rank,
                "generated_answer": "N/A (Retrieval Only)",
                "correctness": None,
                "faithfulness": None,
                "latency_seconds": round(elapsed, 2),
            })
            # Incremental save so crashes don't lose progress
            with open(RUNS_DIR / "latest_run.json", "w", encoding="utf-8") as _f:
                json.dump({"summary": {"split": split, "tag": tag, "partial": True}, "results": results}, _f, indent=2)

        # -------------------------------------------------------------
        # Case B: Generation-Focused Question (Retrieval + Answer + Judge)
        # -------------------------------------------------------------
        else:
            # Respect Groq's 8000 TPM free-tier limit (~3500 tokens/call → 1 call per 35s)
            time.sleep(35)
            ans_res = answer_question(
                query=question,
                user_id=USER_ID,
                doc_ids=[DOC_ID],
                top_k=5,
            )
            generated_answer = ans_res.get("answer", "")
            chunks = ans_res.get("retrieved_chunks", [])
            ret_res = grade_retrieval(chunks, expected_page)

            # Grade with Gemini judges
            corr_res = grade_correctness(
                question=question,
                generated_answer=generated_answer,
                ground_truth=ground_truth,
                must_include=must_include,
                must_not_include=must_not_include,
            )
            faith_res = grade_faithfulness(
                generated_answer=generated_answer,
                retrieved_chunks=chunks,
            )

            elapsed = time.time() - t0

            retrieval_hit = ret_res["hit"]
            reciprocal_rank = ret_res["reciprocal_rank"]
            retrieval_count += 1
            if retrieval_hit:
                retrieval_hits += 1
            total_retrieval_mrr += reciprocal_rank

            corr_pass = corr_res.get("verdict") == "PASS"
            faith_pass = faith_res.get("verdict") == "PASS"

            generation_count += 1
            if corr_pass:
                correctness_passes += 1
            if faith_pass:
                faithfulness_passes += 1

            status_corr = "PASS" if corr_pass else "FAIL"
            status_faith = "PASS" if faith_pass else "FAIL"

            print(
                f"[{idx:02d}/{len(tests)}] {test_id} [GENERATION] | Ret: {'PASS' if retrieval_hit else 'FAIL'} | "
                f"Corr: {status_corr} | Faith: {status_faith} | {elapsed:.2f}s | {question[:35]}..."
            )

            results.append({
                "id": test_id,
                "test_stage": test_stage,
                "question": question,
                "expected_page": expected_page,
                "retrieved_pages": ret_res["retrieved_pages"],
                "retrieval_hit": retrieval_hit,
                "reciprocal_rank": reciprocal_rank,
                "generated_answer": generated_answer,
                "ground_truth": ground_truth,
                "correctness": corr_res,
                "faithfulness": faith_res,
                "latency_seconds": round(elapsed, 2),
            })
            # Incremental save so crashes don't lose progress
            with open(RUNS_DIR / "latest_run.json", "w", encoding="utf-8") as _f:
                json.dump({"summary": {"split": split, "tag": tag, "partial": True}, "results": results}, _f, indent=2)

    total_time = time.time() - total_start

    # Metrics Summary
    hit_rate_pct = (retrieval_hits / retrieval_count * 100.0) if retrieval_count else 0.0
    mrr_score = (total_retrieval_mrr / retrieval_count) if retrieval_count else 0.0
    correctness_pct = (correctness_passes / generation_count * 100.0) if generation_count else 0.0
    faithfulness_pct = (faithfulness_passes / generation_count * 100.0) if generation_count else 0.0

    summary = {
        "timestamp": datetime.now().isoformat(),
        "split": split,
        "tag": tag,
        "total_tests": len(tests),
        "total_time_seconds": round(total_time, 1),
        "avg_latency_seconds": round(total_time / len(tests), 2),
        "metrics": {
            "retrieval_hit_at_5_pct": round(hit_rate_pct, 2),
            "retrieval_mrr": round(mrr_score, 3),
            "correctness_pct": round(correctness_pct, 2),
            "faithfulness_pct": round(faithfulness_pct, 2),
        },
        "counts": {
            "retrieval_hits": f"{retrieval_hits}/{retrieval_count}",
            "correctness_passes": f"{correctness_passes}/{generation_count}",
            "faithfulness_passes": f"{faithfulness_passes}/{generation_count}",
        },
    }

    # Save Run Outputs inside evals/step_5_results/
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_file = RUNS_DIR / f"run_{split}_{tag}_{timestamp_str}.json"
    latest_file = RUNS_DIR / "latest_run.json"

    run_payload = {"summary": summary, "results": results}
    with open(run_file, "w", encoding="utf-8") as f:
        json.dump(run_payload, f, indent=2)
    with open(latest_file, "w", encoding="utf-8") as f:
        json.dump(run_payload, f, indent=2)

    # Save to baseline.json if baseline run
    if tag == "baseline":
        baseline_file = RESULTS_DIR / "baseline.json"
        with open(baseline_file, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)

    print("\n=================================================================")
    print("  EVALUATION SUMMARY")
    print("=================================================================")
    print(f"Dataset Split:       {split.upper()} ({len(tests)} questions)")
    print(f"Total Time:          {total_time:.1f}s (Avg {total_time / len(tests):.2f}s per query)")
    print(f"Retrieval Hit@5:     {hit_rate_pct:.1f}% ({retrieval_hits}/{retrieval_count})")
    print(f"Retrieval MRR:       {mrr_score:.3f}")
    print(f"Answer Correctness:  {correctness_pct:.1f}% ({correctness_passes}/{generation_count})")
    print(f"Answer Faithfulness: {faithfulness_pct:.1f}% ({faithfulness_passes}/{generation_count})")
    print("-----------------------------------------------------------------")
    print(f"Saved run details:   {run_file.name}")
    print("=================================================================\n")

    return summary, results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LedgerLens Evaluation Runner")
    parser.add_argument("--split", choices=["dev", "test"], default="dev", help="Dataset split to evaluate")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of tests")
    parser.add_argument("--tag", type=str, default="baseline", help="Tag for this run (e.g. baseline, tuned)")
    parser.add_argument("--resume", action="store_true", help="Resume from latest_run.json (skip already-done questions)")
    args = parser.parse_args()

    run_evaluation(split=args.split, limit=args.limit, tag=args.tag, resume=args.resume)
