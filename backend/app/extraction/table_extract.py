"""
Table extraction module.
"""

from typing import List, Dict, Any, Optional
import pymupdf


def is_valid_financial_table(table_data: List[List[str]]) -> bool:

    if not table_data or len(table_data) < 2:
        return False

    total_non_empty_cells = 0
    numeric_cells = 0

    for row in table_data:
        for cell in row:
            text = str(cell).strip() if cell is not None else ""
            if not text:
                continue

            words = text.split()
            # If a cell is a long paragraph of prose, it's a text column, not a table cell
            if len(words) > 35:
                return False

            total_non_empty_cells += 1

            # Check for financial indicators: digits, currency, %, or parentheses around numbers (e.g. (1,234))
            has_digit = any(ch.isdigit() for ch in text)
            has_symbol = any(sym in text for sym in ["$", "€", "£", "¥", "%"])
            if has_digit or has_symbol:
                numeric_cells += 1

    if total_non_empty_cells == 0:
        return False

    # Genuine financial tables have numbers. Require at least 15% numeric density.
    if (numeric_cells / total_non_empty_cells) < 0.15:
        return False

    return True


def extract_page_tables(
    page: pymupdf.Page,
    page_number: int,
) -> List[Dict[str, Any]]:
    """
    Extracts all validated financial tables from a single page using PyMuPDF table finder.

    Returns structured representation:
    [
        {
            "page_number": int,
            "table_index": int,
            "bbox": [x0, y0, x1, y1],
            "headers": List[str],
            "rows": List[List[str]],
            "markdown": str,
            "cells": [
                {
                    "row": int,
                    "col": int,
                    "row_header": str,
                    "col_header": str,
                    "value": str,
                    "table_bbox": [x0, y0, x1, y1]
                },
                ...
            ]
        }
    ]
    """
    extracted_tables: List[Dict[str, Any]] = []

    try:
        table_finder = page.find_tables()
    except Exception:
        return extracted_tables

    if not table_finder or not table_finder.tables:
        return extracted_tables

    valid_tbl_idx = 0
    for raw_table in table_finder.tables:
        raw_bbox = [round(float(c), 2) for c in raw_table.bbox]

        # Extract rows
        table_data = raw_table.extract()
        if not table_data or len(table_data) == 0:
            continue

        # Clean string rows
        cleaned_rows = [
            [str(cell).strip() if cell is not None else "" for cell in row]
            for row in table_data
        ]

        # Guard: Check if this is a genuine financial table or side-by-side text columns
        if not is_valid_financial_table(cleaned_rows):
            continue

        headers = cleaned_rows[0] if cleaned_rows else []
        body_rows = cleaned_rows[1:] if len(cleaned_rows) > 1 else []

        # Convert to markdown representation for LLM chunking
        markdown_representation = _table_to_markdown(cleaned_rows)

        # Parse cell relationships for verifiable financial lookup
        cells_metadata: List[Dict[str, Any]] = []
        for r_idx, row in enumerate(cleaned_rows):
            row_header = row[0] if len(row) > 0 else ""
            for c_idx, val in enumerate(row):
                if not val:
                    continue
                col_header = headers[c_idx] if c_idx < len(headers) else f"Col_{c_idx}"
                cells_metadata.append(
                    {
                        "row": r_idx,
                        "col": c_idx,
                        "row_header": row_header,
                        "col_header": col_header,
                        "value": val,
                        "table_bbox": raw_bbox,
                    }
                )

        extracted_tables.append(
            {
                "page_number": page_number,
                "table_index": valid_tbl_idx,
                "bbox": raw_bbox,
                "headers": headers,
                "rows": body_rows,
                "markdown": markdown_representation,
                "cells": cells_metadata,
                "type": "table",
            }
        )
        valid_tbl_idx += 1

    return extracted_tables


def extract_tables(
    pdf_source: Any,
) -> List[Dict[str, Any]]:

    if isinstance(pdf_source, (bytes, bytearray)):
        doc = pymupdf.open(stream=pdf_source, filetype="pdf")
    else:
        doc = pymupdf.open(pdf_source)

    all_tables: List[Dict[str, Any]] = []

    try:
        for page_idx in range(len(doc)):
            page_number = page_idx + 1
            page = doc[page_idx]
            page_tables = extract_page_tables(page, page_number)
            all_tables.extend(page_tables)
    finally:
        doc.close()

    return all_tables


def get_table_bboxes_by_page(
    tables: List[Dict[str, Any]],
) -> Dict[int, List[List[float]]]:

    table_regions: Dict[int, List[List[float]]] = {}
    for tbl in tables:
        page_num = tbl["page_number"]
        if page_num not in table_regions:
            table_regions[page_num] = []
        table_regions[page_num].append(tbl["bbox"])
    return table_regions


def _table_to_markdown(rows: List[List[str]]) -> str:
    if not rows:
        return ""

    num_cols = max(len(row) for row in rows)
    normalized_rows = [row + [""] * (num_cols - len(row)) for row in rows]

    header = normalized_rows[0]
    separator = ["---"] * num_cols

    lines = ["| " + " | ".join(header) + " |", "| " + " | ".join(separator) + " |"]

    for body_row in normalized_rows[1:]:
        lines.append("| " + " | ".join(body_row) + " |")

    return "\n".join(lines)
