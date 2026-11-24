"""
OCR extraction module for LedgerLens.
Detects scanned / image-only PDF pages and runs OCR with intelligent fallback:
1. If page has < 50 words -> treated as scanned/visual page.
2. Runs Tesseract OCR with coordinates and confidence scoring.
3. If OCR confidence drops below threshold (default: 65%), falls back to
   a Vision Language Model (VLM via Groq) using vlm_ocr_v1.txt prompt for
   high-accuracy transcription of degraded financial text and scanned tables.
"""

import os
import io
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf
import pytesseract
from PIL import Image
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from config.setting import GROQ_API_KEY

# Ensure Tesseract executable path on Windows if not already in system PATH
DEFAULT_TESSERACT_WINDOWS_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
if os.path.exists(DEFAULT_TESSERACT_WINDOWS_PATH) and not getattr(
    pytesseract.pytesseract, "tesseract_cmd", ""
).endswith("tesseract.exe"):
    pytesseract.pytesseract.tesseract_cmd = DEFAULT_TESSERACT_WINDOWS_PATH

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_PROMPT_VERSION = "v1"


# load the ocr propmt
def load_ocr_vlm_prompt(version: str = DEFAULT_PROMPT_VERSION) -> str:
    """
    Reads the VLM OCR fallback prompt template.
    Path: backend/app/prompts/{version}/vlm_ocr_{version}.txt
    """
    prompt_file = PROMPTS_DIR / version / f"vlm_ocr_{version}.txt"
    if prompt_file.exists():
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    return "Transcribe all text, numbers, and tables from this scanned document with 100% accuracy."


# check if the page is scan one
def is_scanned_page(
    page: pymupdf.Page,
    min_word_threshold: int = 50,
) -> bool:
    """
    Determines if a PDF page is a scanned document / pure image.
    If the embedded digital text stream has fewer than min_word_threshold words,
    it is treated as a scanned page requiring OCR.

    Args:
        page: PyMuPDF Page object.
        min_word_threshold: Minimum word count to qualify as a native digital text page.

    Returns:
        True if the page appears scanned (< 50 words), False otherwise.
    """
    raw_text = page.get_text().strip()
    word_count = len(raw_text.split())
    return word_count < min_word_threshold


# render the page into high resolution image type
def render_page_to_image(
    page: pymupdf.Page,
    dpi: int = 200,
) -> Image.Image:
    """
    Renders a PDF page to a high-resolution PIL Image suitable for OCR or VLM.
    """
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix)
    img_bytes = pix.tobytes("png")
    return Image.open(io.BytesIO(img_bytes))


# if the confidence of extraction is less then 80 then send it to vlm
def ocr_page_with_vlm_fallback(
    page: pymupdf.Page,
    page_number: int,
    confidence_threshold: float = 80.0,
    dpi: int = 200,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    model_name: str = "llama-3.2-11b-vision-preview",
) -> List[Dict[str, Any]]:

    pil_img = render_page_to_image(page, dpi=dpi)
    scale_factor = 72.0 / dpi
    page_rect = page.rect
    full_page_bbox = [
        round(float(page_rect.x0), 2),
        round(float(page_rect.y0), 2),
        round(float(page_rect.x1), 2),
        round(float(page_rect.y1), 2),
    ]

    tesseract_success = False
    average_conf = 0.0
    grouped_blocks: Dict[int, Dict[str, Any]] = {}

    try:
        data = pytesseract.image_to_data(pil_img, output_type=pytesseract.Output.DICT)
        num_entries = len(data["text"])
        all_conf_scores: List[float] = []

        for i in range(num_entries):
            word = data["text"][i].strip()
            conf = float(data["conf"][i])

            # Tesseract uses -1 for block/par/line headers
            if conf >= 0:
                all_conf_scores.append(conf)

            if not word or conf < 15.0:
                continue

            b_num = data["block_num"][i]
            x, y, w, h = (
                data["left"][i],
                data["top"][i],
                data["width"][i],
                data["height"][i],
            )

            if b_num not in grouped_blocks:
                grouped_blocks[b_num] = {
                    "words": [word],
                    "left": x,
                    "top": y,
                    "right": x + w,
                    "bottom": y + h,
                    "conf_scores": [conf],
                }
            else:
                grouped_blocks[b_num]["words"].append(word)
                grouped_blocks[b_num]["left"] = min(grouped_blocks[b_num]["left"], x)
                grouped_blocks[b_num]["top"] = min(grouped_blocks[b_num]["top"], y)
                grouped_blocks[b_num]["right"] = max(
                    grouped_blocks[b_num]["right"], x + w
                )
                grouped_blocks[b_num]["bottom"] = max(
                    grouped_blocks[b_num]["bottom"], y + h
                )
                grouped_blocks[b_num]["conf_scores"].append(conf)

        if all_conf_scores:
            average_conf = sum(all_conf_scores) / len(all_conf_scores)
            tesseract_success = True

    except Exception:
        tesseract_success = False
        average_conf = 0.0

    # Decision: Did Tesseract succeed with confidence >= threshold?
    # If YES: return the high-confidence Tesseract blocks with their exact coordinates
    if tesseract_success and average_conf >= confidence_threshold and grouped_blocks:
        extracted_blocks: List[Dict[str, Any]] = []
        for idx, (b_num, block_info) in enumerate(grouped_blocks.items()):
            text = " ".join(block_info["words"]).strip()
            if not text:
                continue

            x0 = round(block_info["left"] * scale_factor, 2)
            y0 = round(block_info["top"] * scale_factor, 2)
            x1 = round(block_info["right"] * scale_factor, 2)
            y1 = round(block_info["bottom"] * scale_factor, 2)
            block_conf = sum(block_info["conf_scores"]) / len(block_info["conf_scores"])

            extracted_blocks.append(
                {
                    "page_number": page_number,
                    "block_index": idx,
                    "text": text,
                    "bbox": [x0, y0, x1, y1],
                    "confidence": round(block_conf, 1),
                    "method": "tesseract",
                    "type": "scanned_text",
                }
            )
        return extracted_blocks

    # If NO (confidence < threshold or Tesseract failed): Trigger VLM Fallback
    vlm_text = _call_vlm_for_page(
        pil_img, prompt_version=prompt_version, model_name=model_name
    )

    return [
        {
            "page_number": page_number,
            "block_index": 0,
            "text": vlm_text,
            "bbox": full_page_bbox,
            "confidence": 98.0,  # VLM transcription confidence
            "method": "vlm_fallback",
            "tesseract_conf_was": round(average_conf, 1),
            "type": "scanned_text",
        }
    ]


def _call_vlm_for_page(
    pil_img: Image.Image,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
    model_name: str = "llama-3.2-11b-vision-preview",
) -> str:
    """
    Sends the rendered page image to Groq's Vision Language Model.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set for VLM OCR fallback.")

    prompt = load_ocr_vlm_prompt(version=prompt_version)

    buffered = io.BytesIO()
    pil_img.save(buffered, format="PNG")
    base64_image = base64.b64encode(buffered.getvalue()).decode("utf-8")

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


def extract_scanned_pages(
    pdf_source: Any,
    min_word_threshold: int = 50,
    confidence_threshold: float = 80.0,
    dpi: int = 200,
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> Dict[str, Any]:

    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    scanned_pages: List[int] = []
    all_ocr_blocks: List[Dict[str, Any]] = []

    try:
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]

            if is_scanned_page(page, min_word_threshold=min_word_threshold):
                scanned_pages.append(page_number)
                blocks = ocr_page_with_vlm_fallback(
                    page,
                    page_number,
                    confidence_threshold=confidence_threshold,
                    dpi=dpi,
                    prompt_version=prompt_version,
                )
                all_ocr_blocks.extend(blocks)
    finally:
        doc.close()

    return {
        "scanned_pages_indices": scanned_pages,
        "ocr_blocks": all_ocr_blocks,
    }
