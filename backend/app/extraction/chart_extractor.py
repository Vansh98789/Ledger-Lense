"""
Chart extraction and VLM analysis module for LedgerLens.
Detects financial charts, graphs, and visual plots (both raster and vector graphics),
crops the chart bounding box as high-resolution image bytes,
and utilizes a Vision Language Model (VLM via Groq) to convert visual chart data
into structured Markdown tables and factual summaries.
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


def load_chart_prompt(version: str = DEFAULT_PROMPT_VERSION) -> str:
    """
    Reads the VLM chart prompt template from the versioned prompt directory.
    Explicitly targets: backend/app/prompts/{version}/vlm_chart_{version}.txt
    """
    prompt_file = PROMPTS_DIR / version / f"vlm_chart_{version}.txt"
    if prompt_file.exists():
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    raise FileNotFoundError(f"VLM chart prompt not found at: {prompt_file}")


def detect_page_chart_regions(
    page: pymupdf.Page,
    min_width: float = 120.0,
    min_height: float = 80.0,
) -> List[List[float]]:
    """
    Detects potential chart regions on a page.
    Financial charts are typically created with vector drawing paths
    (lines, rects, curves for bar/line charts) or embedded high-res images.

    Returns:
        List of bounding boxes [[x0, y0, x1, y1], ...]
    """
    chart_bboxes: List[List[float]] = []

    # 1. Inspect vector drawings (standard for SEC filings / corporate PDF charts)
    try:
        drawings = page.get_drawings()
    except Exception:
        drawings = []

    # Group drawings with tight spatial clustering that have many paths (lines/curves)
    if drawings and len(drawings) >= 5:
        # Compute bounding rectangle enclosing dense clusters of drawings
        rects = [d["rect"] for d in drawings if "rect" in d]
        if rects:
            # Cluster drawings into candidate chart areas
            clusters = _cluster_rectangles(rects, page.rect)
            for cluster_bbox in clusters:
                w = cluster_bbox[2] - cluster_bbox[0]
                h = cluster_bbox[3] - cluster_bbox[1]
                # Filter out tiny underline decorations or full-page backgrounds
                if min_width <= w < (page.rect.width * 0.95) and min_height <= h < (page.rect.height * 0.85):
                    chart_bboxes.append(cluster_bbox)

    # 2. Inspect embedded raster images that match chart aspect ratios
    image_list = page.get_images(full=True)
    for img_info in image_list:
        xref = img_info[0]
        rects = page.get_image_rects(xref)
        for r in rects:
            w = r.x1 - r.x0
            h = r.y1 - r.y0
            if w >= min_width and h >= min_height and w < (page.rect.width * 0.95):
                bbox = [round(float(r.x0), 2), round(float(r.y0), 2),
                        round(float(r.x1), 2), round(float(r.y1), 2)]
                if not _is_overlapping_any(bbox, chart_bboxes):
                    chart_bboxes.append(bbox)

    return chart_bboxes


def crop_region_to_image_bytes(
    page: pymupdf.Page,
    bbox: List[float],
    dpi: int = 150,
) -> bytes:
    """
    Renders and crops a specific bounding box on a PDF page into PNG bytes.

    Args:
        page: PyMuPDF Page object.
        bbox: [x0, y0, x1, y1] coordinates in page points.
        dpi: Target resolution for VLM quality.

    Returns:
        Raw PNG bytes of the cropped region.
    """
    rect = pymupdf.Rect(*bbox)
    zoom = dpi / 72.0
    matrix = pymupdf.Matrix(zoom, zoom)
    pix = page.get_pixmap(matrix=matrix, clip=rect)
    return pix.tobytes(output="png")


def analyze_chart_with_vlm(
    chart_image_bytes: bytes,
    model_name: str = "llama-3.2-11b-vision-preview",
    prompt_version: str = DEFAULT_PROMPT_VERSION,
) -> str:
    """
    Sends a cropped chart image to Groq's Vision Language Model using the
    prompt loaded from backend/app/prompts/{prompt_version}/vlm_chart_{prompt_version}.txt.

    Args:
        chart_image_bytes: PNG bytes of the chart area.
        model_name: Vision-capable Groq model.
        prompt_version: Version of prompt to use (e.g. 'v1', 'v2').

    Returns:
        Structured Markdown table and factual trend summary.
    """
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY is not set.")

    system_prompt = load_chart_prompt(version=prompt_version)
    base64_image = base64.b64encode(chart_image_bytes).decode("utf-8")

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
                "image_url": {"url": f"data:image/png;base64,{base64_image}"},
            },
        ]
    )

    response = llm.invoke([message])
    return response.content if hasattr(response, "content") else str(response)


def extract_charts(
    pdf_source: Any,
    analyze_vlm: bool = False,
) -> List[Dict[str, Any]]:
    """
    Extracts all chart regions across all pages of a PDF document.

    Args:
        pdf_source: File path (str) or PDF raw bytes.
        analyze_vlm: If True, calls VLM to generate markdown tables and summaries.

    Returns:
        List of chart records with bounding boxes and optional VLM analyses.
    """
    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    all_charts: List[Dict[str, Any]] = []

    try:
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]
            chart_bboxes = detect_page_chart_regions(page)

            for c_idx, bbox in enumerate(chart_bboxes):
                image_bytes = crop_region_to_image_bytes(page, bbox)

                chart_entry = {
                    "page_number": page_number,
                    "chart_index": c_idx,
                    "bbox": bbox,
                    "image_bytes": image_bytes,
                    "type": "chart",
                }

                if analyze_vlm:
                    try:
                        analysis = analyze_chart_with_vlm(image_bytes)
                        chart_entry["analysis"] = analysis
                    except Exception as e:
                        chart_entry["analysis"] = f"[VLM analysis error: {str(e)}]"

                all_charts.append(chart_entry)
    finally:
        doc.close()

    return all_charts


def get_chart_bboxes_by_page(charts: List[Dict[str, Any]]) -> Dict[int, List[List[float]]]:
    """
    Helper function to aggregate chart bounding boxes grouped by page.
    Used by text_extract to prevent duplicate extraction of chart regions.
    """
    regions: Dict[int, List[List[float]]] = {}
    for ch in charts:
        page_num = ch["page_number"]
        if page_num not in regions:
            regions[page_num] = []
        regions[page_num].append(ch["bbox"])
    return regions


def _cluster_rectangles(rects: List[pymupdf.Rect], page_rect: pymupdf.Rect, margin: float = 15.0) -> List[List[float]]:
    """
    Combines adjacent or overlapping drawing rectangles into unified bounding boxes.
    """
    if not rects:
        return []

    # Filter out empty or whole-page rects
    valid_rects = [
        r for r in rects
        if r.width > 5 and r.height > 5 and r.width < (page_rect.width * 0.95)
    ]

    if not valid_rects:
        return []

    # Union all valid drawing clusters
    union_rect = valid_rects[0]
    for r in valid_rects[1:]:
        union_rect = union_rect | r

    return [[
        round(float(union_rect.x0), 2),
        round(float(union_rect.y0), 2),
        round(float(union_rect.x1), 2),
        round(float(union_rect.y1), 2)
    ]]


def _is_overlapping_any(bbox: List[float], bboxes: List[List[float]], threshold: float = 0.4) -> bool:
    """Returns True if bbox overlaps significantly with any bbox in the list."""
    bx0, by0, bx1, by1 = bbox
    b_area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    if b_area <= 0:
        return False

    for ox0, oy0, ox1, oy1 in bboxes:
        ix0 = max(bx0, ox0)
        iy0 = max(by0, oy0)
        ix1 = min(bx1, ox1)
        iy1 = min(by1, oy1)

        if ix1 > ix0 and iy1 > iy0:
            intersect_area = (ix1 - ix0) * (iy1 - iy0)
            if (intersect_area / b_area) >= threshold:
                return True
    return False
