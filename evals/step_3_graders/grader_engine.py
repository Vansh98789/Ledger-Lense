import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure backend can be imported
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from dotenv import load_dotenv
load_dotenv(BACKEND_DIR / ".env")

from langchain_core.messages import HumanMessage, SystemMessage
from app.retrieval.generator import get_qa_llm

PROMPTS_DIR = Path(__file__).parent / "prompts"
_judge_llm = None


def get_judge_llm():
    """
    Returns Gemini LLM for judging if GEMINI_API_KEY is configured.
    Decouples evaluator from application model (Groq) to eliminate self-preference bias.
    """
    global _judge_llm
    if _judge_llm is not None:
        return _judge_llm

    gemini_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if gemini_key:
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            model_name = os.getenv("GEMINI_JUDGE_MODEL", "gemini-3.5-flash-lite")
            _judge_llm = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=gemini_key,
                temperature=0.0,
            )
            return _judge_llm
        except Exception as e:
            print(f"[WARN] Failed to initialize Gemini judge ({e}), falling back to Groq.")

    _judge_llm = get_qa_llm()
    return _judge_llm


def load_judge_prompt(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"Judge prompt not found at: {path}")
    return path.read_text(encoding="utf-8").strip()


def extract_text_content(content: Any) -> str:
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
            elif hasattr(item, "text"):
                texts.append(item.text)
            else:
                texts.append(str(item))
        return "\n".join(texts)
    return str(content)


def parse_judge_json(raw_content: Any) -> Dict[str, Any]:
    """Parse JSON output from judge response safely."""
    cleaned = extract_text_content(raw_content).strip()
    # Strip markdown code blocks if present
    cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"^```\s*", "", cleaned)
    cleaned = re.sub(r"```$", "", cleaned).strip()

    match = re.search(r"\{[\s\S]*\}", cleaned)
    if match:
        candidate = match.group(0)
        try:
            return json.loads(candidate)
        except Exception:
            pass

    if "PASS" in cleaned.upper():
        return {"verdict": "PASS", "score": 1.0, "reason": cleaned[:120]}
    return {"verdict": "FAIL", "score": 0.0, "reason": cleaned[:120]}


# =====================================================================
# 1. RETRIEVAL GRADER (Deterministic & Fast)
# =====================================================================
def grade_retrieval(
    retrieved_chunks: List[Dict[str, Any]], 
    expected_page: Any
) -> Dict[str, Any]:
    """
    Computes Hit@K and Reciprocal Rank (MRR component) deterministically.
    """
    retrieved_pages = [c.get("page_number") for c in retrieved_chunks if c.get("page_number") is not None]

    # Handle unanswerable / conversation queries (no page expected)
    if expected_page is None:
        hit = len(retrieved_chunks) == 0
        return {
            "hit": hit,
            "score": 1.0 if hit else 0.0,
            "reciprocal_rank": 1.0 if hit else 0.0,
            "retrieved_pages": retrieved_pages,
            "expected_page": None,
        }

    expected_pages = [expected_page] if isinstance(expected_page, int) else list(expected_page)

    hit = False
    reciprocal_rank = 0.0

    for rank, chunk in enumerate(retrieved_chunks, 1):
        page = chunk.get("page_number")
        if page in expected_pages:
            if not hit:
                hit = True
                reciprocal_rank = 1.0 / rank

    return {
        "hit": hit,
        "score": 1.0 if hit else 0.0,
        "reciprocal_rank": reciprocal_rank,
        "retrieved_pages": retrieved_pages,
        "expected_page": expected_page,
    }


# =====================================================================
# 2. CORRECTNESS GRADER (Rule Filter + Strict Financial Judge)
# =====================================================================
def grade_correctness(
    question: str,
    generated_answer: str,
    ground_truth: str,
    must_include: Optional[List[str]] = None,
    must_not_include: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """
    Checks answer accuracy against ground truth using rules and LLM judge.
    """
    must_include = must_include or []
    must_not_include = must_not_include or []
    norm_answer = generated_answer.lower()

    # Rule 1: Check forbidden strings (e.g. rounded billions like "$14.5 billion")
    for forbidden in must_not_include:
        if forbidden.lower() in norm_answer:
            return {
                "verdict": "FAIL",
                "score": 0.0,
                "reason": f"Violated precision rule: contains forbidden string '{forbidden}'.",
            }

    # Rule 2: LLM Judge comparison
    system_prompt = load_judge_prompt("correctness.txt")
    user_payload = (
        f"Question: {question}\n\n"
        f"Ground Truth Answer: {ground_truth}\n\n"
        f"Generated Answer: {generated_answer}\n\n"
        f"Must Not Include (Forbidden): {must_not_include}"
    )

    llm = get_judge_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_payload),
    ])

    return parse_judge_json(response.content)


# =====================================================================
# 3. FAITHFULNESS GRADER (Groundedness / Hallucination Detection)
# =====================================================================
def grade_faithfulness(
    generated_answer: str,
    retrieved_chunks: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Checks if every claim in the answer is grounded in the retrieved chunks.
    """
    if not retrieved_chunks:
        # If no chunks and model says not found, it's faithful
        if "not found" in generated_answer.lower() or "not contain" in generated_answer.lower():
            return {"verdict": "PASS", "score": 1.0, "reason": "Accurately refused when no context was retrieved."}
        return {"verdict": "FAIL", "score": 0.0, "reason": "Hallucinated an answer without any retrieved context."}

    context_blocks = []
    for idx, c in enumerate(retrieved_chunks):
        p = c.get("page_number", "?")
        context_blocks.append(f"[Chunk {idx} (Page {p})]:\n{c.get('content', '')}")
    full_context = "\n\n---\n\n".join(context_blocks)

    system_prompt = load_judge_prompt("faithfulness.txt")
    user_payload = (
        f"Retrieved Context:\n{full_context}\n\n"
        f"Generated Answer:\n{generated_answer}"
    )

    llm = get_judge_llm()
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_payload),
    ])

    return parse_judge_json(response.content)
