import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_groq import ChatGroq

from config.setting import GROQ_API_KEY

DEFAULT_QA_MODEL = "openai/gpt-oss-120b"
PROMPTS_DIR = Path(__file__).resolve().parents[1] / "prompts"

_llm: Optional[ChatGroq] = None


def get_qa_llm(model_name: str = DEFAULT_QA_MODEL) -> ChatGroq:
    global _llm
    if _llm is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set.")
        _llm = ChatGroq(
            groq_api_key=GROQ_API_KEY,
            model_name=model_name,
            temperature=0.0,
        )
    return _llm


def load_need_retrieval_prompt(version: str = "v1") -> str:
    prompt_path = PROMPTS_DIR / version / f"need_retrieval_{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"the need retrieval propmpt not found:{prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def load_conversation_answer_prompt(version: str = "v1") -> str:
    prompt_path = PROMPTS_DIR / version / f"conversation_answer_{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"Conversation answer prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def load_qa_prompt(version: str = "v1") -> str:
    prompt_path = PROMPTS_DIR / version / f"qa_{version}.txt"
    if not prompt_path.exists():
        raise FileNotFoundError(f"QA prompt not found: {prompt_path}")
    return prompt_path.read_text(encoding="utf-8").strip()


def format_context(chunks: List[Dict[str, Any]]) -> str:
    blocks: List[str] = []
    for idx, chunk in enumerate(chunks):
        header = (
            f"[{idx}] (type={chunk.get('chunk_type', 'unknown')}, "
            f"page={chunk.get('page_number', 0)}, "
            f"doc_id={chunk.get('doc_id', '')})"
        )
        blocks.append(f"{header}\n{chunk.get('content', '')}")
    return "\n\n---\n\n".join(blocks)


def _parse_llm_json(raw: str) -> Dict[str, Any]:
    cleaned = raw.strip()
    fence_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    if fence_match:
        cleaned = fence_match.group(1)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        return {
            "answer": raw.strip(),
            "confidence": "MEDIUM",
            "used_chunk_indices": [],
        }


def _format_memory(
    summary: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    parts: List[str] = []
    if summary:
        parts.append(f"Earlier conversation summary:\n{summary}")
    if history:
        turns = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in history)
        parts.append(f"Recent messages:\n{turns}")
    return "\n\n".join(parts)


def rewrite_query_with_history(
    query: str,
    summary: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> str:
    memory_str = _format_memory(summary=summary, history=history)
    if not memory_str:
        return query

    llm = get_qa_llm()
    system_prompt = (
        "Rewrite the user's latest question into a standalone search query using the conversation context. "
        "Resolve pronouns (it, they, that, those) and missing subjects. "
        "If the question is already standalone, return it unchanged. Output ONLY the rewritten query."
    )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{memory_str}\n\nLatest question: {query}"),
        ]
    )
    rewritten = str(response.content).strip()
    return rewritten or query


def summarize_messages(
    existing_summary: Optional[str],
    messages: List[Dict[str, str]],
) -> str:
    turns = "\n".join(f"{m['role'].capitalize()}: {m['content']}" for m in messages)
    prior = f"Existing summary:\n{existing_summary}\n\n" if existing_summary else ""
    llm = get_qa_llm()
    system_prompt = (
        "Update the running summary of a financial document Q&A conversation. "
        "Preserve key entities, metrics, figures, and document topics discussed. Keep it concise (under 150 words)."
    )
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=f"{prior}New turns to fold in:\n{turns}"),
        ]
    )
    return str(response.content).strip()


def generate_answer(
    question: str,
    chunks: List[Dict[str, Any]],
    prompt_version: str = "v1",
    summary: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    if not chunks:
        return {
            "answer": "Not found in the document.",
            "confidence": "NOT_FOUND",
            "citations": [],
            "retrieved_chunks": [],
        }

    system_prompt = load_qa_prompt(version=prompt_version)
    context_str = format_context(chunks)
    memory_str = _format_memory(summary=summary, history=history)
    memory_block = f"Conversation History:\n{memory_str}\n\n" if memory_str else ""
    user_prompt = f"{memory_block}Context:\n{context_str}\n\nQuestion: {question}"

    llm = get_qa_llm()
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )

    parsed = _parse_llm_json(str(response.content))
    answer = parsed.get("answer", "Not found in the document.")
    confidence = parsed.get("confidence", "MEDIUM")
    indices = parsed.get("used_chunk_indices", [])

    citations: List[Dict[str, Any]] = []
    for idx in indices:
        if isinstance(idx, int) and 0 <= idx < len(chunks):
            c = chunks[idx]
            citations.append(
                {
                    "chunk_id": c.get("id"),
                    "doc_id": c.get("doc_id"),
                    "page_number": c.get("page_number"),
                    "chunk_type": c.get("chunk_type"),
                    "bbox": c.get("bbox", []),
                    "rerank_score": c.get("rerank_score"),
                }
            )

    return {
        "answer": answer,
        "confidence": confidence,
        "citations": citations,
        "retrieved_chunks": chunks,
    }


def not_need_retreival(
    query: str,
    prompt_version: str = "v1",
    summary: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> bool:
    system_prompt = load_need_retrieval_prompt(version=prompt_version)
    memory_str = _format_memory(summary=summary, history=history)
    user_question = (
        f"{memory_str}\n\nQuestion: {query}" if memory_str else f"Question: {query}"
    )
    llm = get_qa_llm()
    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_question)]
    )
    return str(response.content).strip().upper() == "FALSE"


def conversation_answer(
    query: str,
    prompt_version: str = "v1",
    summary: Optional[str] = None,
    history: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    system_prompt = load_conversation_answer_prompt(version=prompt_version)
    memory_str = _format_memory(summary=summary, history=history)
    user_question = (
        f"{memory_str}\n\nQuestion: {query}" if memory_str else f"Question: {query}"
    )
    llm = get_qa_llm()
    response = llm.invoke(
        [SystemMessage(content=system_prompt), HumanMessage(content=user_question)]
    )
    return {
        "answer": str(response.content).strip(),
        "confidence": "CONVERSATIONAL",
        "citations": [],
        "retrieved_chunks": [],
    }
