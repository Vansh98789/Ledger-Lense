import io
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from config.setting import GROQ_API_KEY


PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_PROMPT_VERSION = "v1"


def load_ocr_crop_prompt(version: str = DEFAULT_PROMPT_VERSION) -> str:
    prompt_file = PROMPTS_DIR / version / f"vlm_ocr_{version}.txt"
    if prompt_file.exists():
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Transcribe all text, numbers, and tables from this cropped document section with 100% accuracy."


def compute_bbox_union(bboxes: List[List[float]]) -> List[float]:

    if not bboxes:
        return [0.0, 0.0, 0.0, 0.0]

    min_x0 = min(b[0] for b in bboxes)
    min_y0 = min(b[1] for b in bboxes)
    max_x1 = max(b[2] for b in bboxes)
    max_y1 = max(b[3] for b in bboxes)

    return [round(min_x0, 2), round(min_y0, 2), round(max_x1, 2), round(max_y1, 2)]


def rescan_crop_with_vlm(
    pdf_source: Any,
    page_number: int,
    bbox: List[float],
    dpi: int = 200,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    model_name: str = "llama-3.2-11b-vision-preview",
) -> str:

    if not GROQ_API_KEY:
        return "[Error: GROQ_API_KEY not configured for VLM rescan]"

    # Open PDF and locate page
    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    try:
        page = doc[page_number - 1]
        rect = pymupdf.Rect(*bbox)
        zoom = dpi / 72.0
        matrix = pymupdf.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=matrix, clip=rect)
        crop_bytes = pix.tobytes("png")
    finally:
        doc.close()

    base64_image = base64.b64encode(crop_bytes).decode("utf-8")
    prompt = load_ocr_crop_prompt(version=prompt_version)

    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=model_name,
        temperature=0.1,
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            },
        ]
    )

    response = llm.invoke([message])
    return response.content if hasattr(response, "content") else str(response)


def merge_scanned_block_group(
    group: List[Dict[str, Any]],
    page_number: int,
    pdf_source: Optional[Any] = None,
    confidence_threshold: float = 65.0,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> Dict[str, Any]:

    combined_text = "\n\n".join(b["content"] for b in group if b.get("content"))
    all_bboxes = [b["bbox"] for b in group if b.get("bbox")]
    union_bbox = compute_bbox_union(all_bboxes)

    conf_scores: List[float] = []
    methods = set()
    block_indices: List[int] = []

    for b in group:
        meta = b.get("metadata", {})
        if "confidence" in meta:
            conf_scores.append(float(meta["confidence"]))
        if "method" in meta:
            methods.add(meta["method"])
        if "block_index" in meta:
            block_indices.append(meta["block_index"])

    avg_conf = round(sum(conf_scores) / len(conf_scores), 1) if conf_scores else 0.0
    primary_method = "vlm_fallback" if "vlm_fallback" in methods else "tesseract"

    # Targeted VLM Fallback: If confidence is below threshold, re-scan ONLY this crop!
    rescanned_with_vlm = False
    if avg_conf < confidence_threshold and pdf_source is not None:
        try:
            vlm_clean_text = rescan_crop_with_vlm(
                pdf_source=pdf_source,
                page_number=page_number,
                bbox=union_bbox,
                prompt_version=prompt_version,
            )
            if vlm_clean_text and not vlm_clean_text.startswith("[Error:"):
                combined_text = vlm_clean_text.strip()
                primary_method = "vlm_targeted_rescan"
                rescanned_with_vlm = True
                avg_conf = 98.0  # High confidence transcription from VLM
        except Exception as e:
            # Keep original tesseract text if VLM call fails
            pass

    return {
        "page_number": page_number,
        "type": "scanned_text",
        "content": combined_text.strip(),
        "bbox": union_bbox,
        "metadata": {
            "source_type": "scanned_ocr",
            "ocr_method": primary_method,
            "average_confidence": avg_conf,
            "rescanned_with_vlm": rescanned_with_vlm,
            "block_count": len(group),
            "block_indices": block_indices,
            "word_count": len(combined_text.split()),
            "sub_bboxes": all_bboxes,
        },
    }


def chunk_scanned_items(
    items: List[Dict[str, Any]],
    pdf_source: Optional[Any] = None,
    max_words_per_chunk: int = 250,
    overlap_blocks: int = 1,
    confidence_threshold: float = 65.0,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> List[Dict[str, Any]]:

    if not items:
        return []

    scanned_items = [it for it in items if it.get("type") == "scanned_text"]
    if not scanned_items:
        return []

    pages_dict: Dict[int, List[Dict[str, Any]]] = {}
    for item in scanned_items:
        p = item["page_number"]
        if p not in pages_dict:
            pages_dict[p] = []
        pages_dict[p].append(item)

    chunks: List[Dict[str, Any]] = []

    for page_num in sorted(pages_dict.keys()):
        page_blocks = pages_dict[page_num]

        current_group: List[Dict[str, Any]] = []
        current_words = 0

        for block in page_blocks:
            content = block.get("content", "")
            words_in_block = len(content.split())

            if current_words + words_in_block > max_words_per_chunk and current_group:
                chunks.append(
                    merge_scanned_block_group(
                        group=current_group,
                        page_number=page_num,
                        pdf_source=pdf_source,
                        confidence_threshold=confidence_threshold,
                        prompt_version=prompt_version,
                    )
                )

                if overlap_blocks > 0 and len(current_group) >= overlap_blocks:
                    overlap = current_group[-overlap_blocks:]
                else:
                    overlap = []

                current_group = list(overlap)
                current_words = sum(
                    len(b.get("content", "").split()) for b in current_group
                )

            current_group.append(block)
            current_words += words_in_block

        if current_group:
            chunks.append(
                merge_scanned_block_group(
                    group=current_group,
                    page_number=page_num,
                    pdf_source=pdf_source,
                    confidence_threshold=confidence_threshold,
                    prompt_version=prompt_version,
                )
            )

    return chunks
