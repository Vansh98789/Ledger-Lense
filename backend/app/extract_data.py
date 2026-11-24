"""
Main extraction orchestrator for LedgerLens.
Orchestrates the complete document extraction pipeline per page:
1. Opens PDF (filepath or bytes) with PyMuPDF.
2. Checks word count:
   - If < threshold (default: 50 words) -> routes page to OCR/VLM pipeline (scan_ocr_extract.py).
   - If >= threshold -> routes to digital pipeline:
       a. Extract Tables (table_extract.py)
       b. Extract Charts (chart_extractor.py)
       c. Extract Embedded Images (image_extract.py)
       d. Aggregate all table, chart, and image bounding boxes as ignore_rects
       e. Extract narrative Text blocks outside ignore_rects (text_extract.py)
3. Returns unified, coordinate-preserved structured data ready for chunking and pgvector indexing.
"""

from typing import List, Dict, Any, Union
import pymupdf

from app.extraction.text_extract import extract_page_text_blocks
from app.extraction.table_extract import extract_page_tables
from app.extraction.chart_extractor import (
    detect_page_chart_regions,
    crop_region_to_image_bytes,
    analyze_chart_with_vlm,
)
from app.extraction.image_extract import (
    extract_page_images,
    analyze_image_with_vlm,
)
from app.extraction.scan_ocr_extract import (
    is_scanned_page,
    ocr_page_with_vlm_fallback,
)


def extract_data(
    pdf_source: Union[str, bytes, bytearray],
    min_word_threshold: int = 50,
    ocr_confidence_threshold: float = 65.0,
    analyze_vlm: bool = False,
    prompt_version: str = "v1",
) -> List[Dict[str, Any]]:
    """
    Returns:
        List of all extracted elements across all pages:
        [
            {
                "page_number": int,
                "type": "text" | "table" | "chart" | "image" | "scanned_text",
                "content": str (text or markdown representation),
                "bbox": [x0, y0, x1, y1],
                "metadata": dict (e.g. cell info, table index, OCR confidence)
            },
            ...
        ]
    """
    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    all_extracted_items: List[Dict[str, Any]] = []

    try:
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]

            # -------------------------------------------------------------
            # Case 1: Scanned Page (word count < min_word_threshold)
            # -------------------------------------------------------------
            if is_scanned_page(page, min_word_threshold=min_word_threshold):
                ocr_blocks = ocr_page_with_vlm_fallback(
                    page=page,
                    page_number=page_number,
                    confidence_threshold=ocr_confidence_threshold,
                    prompt_version=prompt_version,
                )
                for block in ocr_blocks:
                    all_extracted_items.append(
                        {
                            "page_number": page_number,
                            "type": "scanned_text",
                            "content": block["text"],
                            "bbox": block["bbox"],
                            "metadata": {
                                "method": block.get("method", "tesseract"),
                                "confidence": block.get("confidence", 0.0),
                                "block_index": block.get("block_index", 0),
                            },
                        }
                    )
                continue

            # -------------------------------------------------------------
            # Case 2: Digital Page (word count >= min_word_threshold)
            # -------------------------------------------------------------
            page_ignore_rects: List[List[float]] = []

            # Step 2a: Extract Financial Tables
            page_tables = extract_page_tables(page, page_number)
            for tbl in page_tables:
                page_ignore_rects.append(tbl["bbox"])
                all_extracted_items.append(
                    {
                        "page_number": page_number,
                        "type": "table",
                        "content": tbl["markdown"],
                        "bbox": tbl["bbox"],
                        "metadata": {
                            "table_index": tbl["table_index"],
                            "headers": tbl["headers"],
                            "cells": tbl["cells"],
                        },
                    }
                )

            # Step 2b: Detect & Extract Charts
            chart_bboxes = detect_page_chart_regions(page)
            for c_idx, c_bbox in enumerate(chart_bboxes):
                page_ignore_rects.append(c_bbox)
                chart_img_bytes = crop_region_to_image_bytes(page, c_bbox)

                chart_analysis = ""
                if analyze_vlm:
                    try:
                        chart_analysis = analyze_chart_with_vlm(
                            chart_img_bytes,
                            prompt_version=prompt_version,
                        )
                    except Exception as e:
                        chart_analysis = f"[VLM analysis error: {str(e)}]"

                all_extracted_items.append(
                    {
                        "page_number": page_number,
                        "type": "chart",
                        "content": chart_analysis
                        if chart_analysis
                        else "[Financial Chart Region]",
                        "bbox": c_bbox,
                        "metadata": {
                            "chart_index": c_idx,
                            "has_vlm_analysis": bool(chart_analysis),
                        },
                    }
                )

            # Step 2c: Detect & Extract Embedded Images / Diagrams
            page_images = extract_page_images(page, page_number)
            for img in page_images:
                page_ignore_rects.append(img["bbox"])

                img_description = ""
                if analyze_vlm:
                    try:
                        img_description = analyze_image_with_vlm(
                            img["image_bytes"],
                            image_format=img["image_format"],
                            prompt_version=prompt_version,
                        )
                    except Exception as e:
                        img_description = f"[VLM analysis error: {str(e)}]"

                all_extracted_items.append(
                    {
                        "page_number": page_number,
                        "type": "image",
                        "content": img_description
                        if img_description
                        else "[Visual Diagram/Image]",
                        "bbox": img["bbox"],
                        "metadata": {
                            "image_index": img["image_index"],
                            "width": img["width"],
                            "height": img["height"],
                            "format": img["image_format"],
                        },
                    }
                )

            # Step 2d: Extract Narrative Text (skipping ignore_rects)
            page_text_blocks = extract_page_text_blocks(
                page=page,
                page_number=page_number,
                ignore_rects=page_ignore_rects,
            )
            for txt_block in page_text_blocks:
                all_extracted_items.append(
                    {
                        "page_number": page_number,
                        "type": "text",
                        "content": txt_block["text"],
                        "bbox": txt_block["bbox"],
                        "metadata": {
                            "block_index": txt_block["block_index"],
                        },
                    }
                )

    finally:
        doc.close()

    return all_extracted_items
