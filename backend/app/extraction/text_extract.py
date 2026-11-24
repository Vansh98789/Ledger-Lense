"""
Text extraction module for LedgerLens.
Sorts blocks into natural human reading order, correctly handling:
    1. Single full-width headers/banners spanning across the page.
    2. Multi-column layouts (e.g. 2-column or 3-column financial reports),
       reading Column 1 (top->bottom) before Column 2 (top->bottom).
"""

from typing import List, Dict, Any, Optional
import pymupdf


def sort_blocks_by_reading_order(
    blocks: List[Any], page_width: float, column_gap_threshold: float = 20.0
) -> List[Any]:

    if not blocks:
        return []

    # Filter to text blocks only (block_type == 0)
    text_blocks = [b for b in blocks if len(b) >= 7 and b[6] == 0 and b[4].strip()]
    if not text_blocks:
        return []

    # Detect if page exhibits multi-column characteristics:
    # A block is considered "full width" if it occupies more than 65% of the page width
    midpoint = page_width / 2.0
    has_left_column = False
    has_right_column = False

    for b in text_blocks:
        bx0, _, bx1, _ = b[:4]
        b_width = bx1 - bx0
        # If it's not a full-width header:
        if b_width < (page_width * 0.65):
            if bx1 <= midpoint + column_gap_threshold:
                has_left_column = True
            elif bx0 >= midpoint - column_gap_threshold:
                has_right_column = True

    # If both left and right distinct columns exist, partition into reading bands
    is_multi_column = has_left_column and has_right_column

    if not is_multi_column:
        # Standard single-column sort: top to bottom, then left to right
        return sorted(text_blocks, key=lambda b: (round(b[1], -1), b[0]))

    # For multi-column pages:
    # We group blocks into vertical bands separated by full-width headers
    bands: List[List[Any]] = []
    current_band: List[Any] = []

    # Sort vertically first to detect horizontal dividing banners/headers
    vertically_sorted = sorted(text_blocks, key=lambda b: b[1])

    for b in vertically_sorted:
        bx0, by0, bx1, by1 = b[:4]
        b_width = bx1 - bx0
        is_full_width = b_width >= (page_width * 0.65)

        if is_full_width:
            # Full width block breaks the current column band
            if current_band:
                bands.append(current_band)
                current_band = []
            bands.append([b])
        else:
            current_band.append(b)

    if current_band:
        bands.append(current_band)

    # Now, sort each band:
    final_sorted_blocks: List[Any] = []
    for band in bands:
        if len(band) <= 1:
            final_sorted_blocks.extend(band)
            continue

        # In a multi-column band, separate blocks by column (left vs right)
        left_col = []
        right_col = []

        for b in band:
            bx0, _, bx1, _ = b[:4]
            # Center of the block determines its column assignment
            b_center_x = (bx0 + bx1) / 2.0
            if b_center_x < midpoint:
                left_col.append(b)
            else:
                right_col.append(b)

        # Sort left column top-to-bottom, then right column top-to-bottom
        left_col_sorted = sorted(left_col, key=lambda b: b[1])
        right_col_sorted = sorted(right_col, key=lambda b: b[1])

        final_sorted_blocks.extend(left_col_sorted)
        final_sorted_blocks.extend(right_col_sorted)

    return final_sorted_blocks


def extract_page_text_blocks(
    page: pymupdf.Page,
    page_number: int,
    ignore_rects: Optional[List[List[float]]] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts text blocks from a single PDF page with layout awareness.
    Returns:
        List of dicts representing text blocks sorted in natural reading order:
        [
            {
                "page_number": int,
                "block_index": int,
                "text": str,
                "bbox": [x0, y0, x1, y1],
                "type": "text"
            },
            ...
        ]
    """
    raw_blocks = page.get_text("blocks")
    page_rect = page.rect
    page_width = float(page_rect.width)

    # Sort blocks to preserve multi-column reading flow (preventing interleaved lines)
    ordered_blocks = sort_blocks_by_reading_order(raw_blocks, page_width=page_width)

    extracted_blocks: List[Dict[str, Any]] = []

    for block_idx, block in enumerate(ordered_blocks):
        x0, y0, x1, y1, text, _, block_type = block[:7]

        cleaned_text = text.strip()
        if not cleaned_text:
            continue

        block_bbox = [
            round(float(x0), 2),
            round(float(y0), 2),
            round(float(x1), 2),
            round(float(y1), 2),
        ]

        # Check if block falls inside any ignore_rect (e.g. table area)
        if ignore_rects and _is_inside_any_rect(block_bbox, ignore_rects):
            continue

        extracted_blocks.append(
            {
                "page_number": page_number,
                "block_index": block_idx,
                "text": cleaned_text,
                "bbox": block_bbox,
                "type": "text",
            }
        )

    return extracted_blocks


def extract_text(
    pdf_source: Any,
    table_regions_by_page: Optional[Dict[int, List[List[float]]]] = None,
) -> List[Dict[str, Any]]:
    """
    Extracts text blocks from an entire PDF document (file path or bytes).
    """
    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    all_text_blocks: List[Dict[str, Any]] = []

    try:
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]
            ignore_rects = (
                table_regions_by_page.get(page_number)
                if table_regions_by_page
                else None
            )
            page_blocks = extract_page_text_blocks(
                page, page_number, ignore_rects=ignore_rects
            )
            all_text_blocks.extend(page_blocks)
    finally:
        doc.close()

    return all_text_blocks


def _is_inside_any_rect(
    bbox: List[float], rects: List[List[float]], threshold: float = 0.5
) -> bool:
    """
    Returns True if bbox overlaps significantly with any rect in rects.
    """
    bx0, by0, bx1, by1 = bbox
    b_area = max(0.0, bx1 - bx0) * max(0.0, by1 - by0)
    if b_area <= 0:
        return False

    for rx0, ry0, rx1, ry1 in rects:
        # compute intersection
        ix0 = max(bx0, rx0)
        iy0 = max(by0, ry0)
        ix1 = min(bx1, rx1)
        iy1 = min(by1, ry1)

        if ix1 > ix0 and iy1 > iy0:
            intersect_area = (ix1 - ix0) * (iy1 - iy0)
            if (intersect_area / b_area) >= threshold:
                return True

    return False
