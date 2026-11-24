"""
Image extraction and VLM analysis module for LedgerLens.
Extracts embedded images, figures, and diagrams from PDF pages using PyMuPDF.
Filters out tiny icons/decorative artifacts, preserves bounding boxes for citation,
and uses a Vision Language Model (VLM via Groq) to describe financial diagrams.
"""

import os
import base64
from pathlib import Path
from typing import List, Dict, Any, Optional
import pymupdf
from langchain_core.messages import HumanMessage
from langchain_groq import ChatGroq

from config.setting import GROQ_API_KEY


# Load prompt template from prompts directory with explicit versioning
PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"
DEFAULT_PROMPT_VERSION = "v1"


def load_image_prompt(version: str = DEFAULT_PROMPT_VERSION) -> str:
    """
    Reads the VLM image prompt template from the versioned prompt directory.
    Explicitly targets: backend/app/prompts/{version}/vlm_image_{version}.txt
    """
    prompt_file = PROMPTS_DIR / version / f"vlm_image_{version}.txt"
    if prompt_file.exists():
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    raise FileNotFoundError(f"VLM image prompt not found at: {prompt_file}")


def extract_page_images(
    page: pymupdf.Page,
    page_number: int,
    min_width: int = 100,
    min_height: int = 100,
) -> List[Dict[str, Any]]:
    """
    Returns:
        List of extracted image metadata dictionaries:
        [
            {
                "page_number": int,
                "image_index": int,
                "bbox": [x0, y0, x1, y1],
                "image_bytes": bytes,
                "image_format": str,
                "type": "image"
            },
            ...
        ]
    """
    extracted_images: List[Dict[str, Any]] = []
    image_list = page.get_images(full=True)

    for img_idx, img_info in enumerate(image_list):
        xref = img_info[0]
        base_image = page.parent.extract_image(xref)
        if not base_image:
            continue

        image_bytes = base_image.get("image")
        image_ext = base_image.get("ext", "png")
        width = base_image.get("width", 0)
        height = base_image.get("height", 0)

        # Filter out tiny icons, logos, bullets, decorative horizontal rules
        if width < min_width or height < min_height:
            continue

        # Find the bounding box on the page where this image is placed
        image_rects = page.get_image_rects(xref)
        if image_rects:
            rect = image_rects[0]
            bbox = [
                round(float(rect.x0), 2),
                round(float(rect.y0), 2),
                round(float(rect.x1), 2),
                round(float(rect.y1), 2),
            ]
        else:
            bbox = [0.0, 0.0, float(width), float(height)]

        extracted_images.append(
            {
                "page_number": page_number,
                "image_index": img_idx,
                "bbox": bbox,
                "image_bytes": image_bytes,
                "image_format": image_ext,
                "width": width,
                "height": height,
                "type": "image",
            }
        )

    return extracted_images


def analyze_image_with_vlm(
    image_bytes: bytes,
    image_format: str = "png",
    model_name: str = "llama-3.2-11b-vision-preview",
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> str:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")

    system_prompt = load_image_prompt(version=prompt_version)
    base64_image = base64.b64encode(image_bytes).decode("utf-8")
    mime_type = (
        f"image/{image_format.lower()}"
        if image_format.lower() != "jpg"
        else "image/jpeg"
    )

    llm = ChatGroq(
        groq_api_key=GROQ_API_KEY,
        model_name=model_name,
        temperature=0.1,
    )

    message = HumanMessage(
        content=[
            {"type": "text", "text": system_prompt},
            {
                "type": "image_url",
                "image_url": {"url": f"data:{mime_type};base64,{base64_image}"},
            },
        ]
    )

    response = llm.invoke([message])
    return response.content if hasattr(response, "content") else str(response)


def extract_images(
    pdf_source: Any,
    analyze_vlm: bool = False,
) -> List[Dict[str, Any]]:

    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    all_images: List[Dict[str, Any]] = []

    try:
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]
            page_images = extract_page_images(page, page_number)

            for img in page_images:
                if analyze_vlm:
                    try:
                        description = analyze_image_with_vlm(
                            img["image_bytes"],
                            image_format=img["image_format"],
                        )
                        img["description"] = description
                    except Exception as e:
                        img["description"] = f"[VLM analysis error: {str(e)}]"

                all_images.append(img)
    finally:
        doc.close()

    return all_images


def get_image_bboxes_by_page(
    images: List[Dict[str, Any]],
) -> Dict[int, List[List[float]]]:

    regions: Dict[int, List[List[float]]] = {}
    for img in images:
        page_num = img["page_number"]
        if page_num not in regions:
            regions[page_num] = []
        regions[page_num].append(img["bbox"])
    return regions
