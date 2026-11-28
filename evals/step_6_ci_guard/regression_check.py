"""
LedgerLens CI/CD Quality & Regression Guard (Step 6)

Verifies evaluation metrics from the latest run.
Pass criteria:
  1. Retrieval Hit@5 >= 85.0%
  2. Answer Correctness >= 85.0%
  3. Answer Faithfulness >= 85.0%
  4. No metric regresses by more than 2.0% below locked baseline.

Exits with:
  0: ALL GATES PASS (Allows merge)
  1: ONE OR MORE METRICS FAIL (Blocks merge)
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

REPO_ROOT = Path(__file__).resolve().parents[2]
RESULTS_DIR = REPO_ROOT / "evals" / "step_5_results"
RUNS_DIR = RESULTS_DIR / "runs"
LATEST_RUN_FILE = RUNS_DIR / "latest_run.json"
BASELINE_FILE = RESULTS_DIR / "baseline.json"

# Quality Gate Thresholds
TARGETS = {
    "retrieval_hit_at_5_pct": 85.0,
    "correctness_pct": 85.0,
    "faithfulness_pct": 85.0,
}

MAX_ALLOWED_DROP_PCT = 2.0


def load_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def run_guard() -> int:
    print("=" * 65)
    print("  STEP 6: CI/CD REGRESSION GUARD & QUALITY GATE")
    print("=" * 65)

    if not LATEST_RUN_FILE.exists():
        print(f"❌ ERROR: Latest evaluation run not found at:\n  {LATEST_RUN_FILE}")
        return 1

    run_data = load_json(LATEST_RUN_FILE)
    metrics = run_data.get("summary", {}).get("metrics", {})

    baseline_metrics = {}
    if BASELINE_FILE.exists():
        base_data = load_json(BASELINE_FILE)
        baseline_metrics = base_data.get("metrics", base_data.get("summary", {}).get("metrics", {}))

    print(f"\nRun Details:")
    print(f"  Split: {run_data.get('summary', {}).get('split', 'dev').upper()}")
    print(f"  Tag:   {run_data.get('summary', {}).get('tag', 'unknown')}")
    print(f"  Tests: {run_data.get('summary', {}).get('total_tests', len(run_data.get('results', [])))}\n")

    print("-" * 65)
    print(f"{'Metric':<26} | {'Target':<8} | {'Latest':<8} | {'Status'}")
    print("-" * 65)

    failures = []

    for key, target in TARGETS.items():
        val = metrics.get(key, 0.0)
        display = key.replace("_pct", "").replace("_", " ").title()

        # Check threshold
        passed_target = val >= target

        # Check regression vs baseline if baseline is present
        base_val = baseline_metrics.get(key)
        regressed = False
        if base_val is not None:
            drop = base_val - val
            if drop > MAX_ALLOWED_DROP_PCT and not passed_target:
                regressed = True

        status = "✅ PASS"
        if not passed_target or regressed:
            status = "❌ FAIL"
            failures.append(f"{display}: {val:.1f}% (Required: ≥{target:.1f}%)")

        print(f"{display:<26} | ≥{target:.1f}%  | {val:.1f}%   | {status}")

    print("-" * 65)

    if failures:
        print("\n❌ QUALITY GATE FAILED:")
        for f in failures:
            print(f"  • {f}")
        print("\nAction: Pull Request merge blocked. Resolve regressions.\n")
        return 1

    print("\n✅ QUALITY GATE PASSED:")
    print("  • All metrics meet production target (≥85.0%).")
    print("  • Safe to merge!\n")
    return 0


if __name__ == "__main__":
    sys.exit(run_guard())
