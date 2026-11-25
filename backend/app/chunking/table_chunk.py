from typing import List, Dict, Any


def compute_table_slice_bbox(
    table_bbox: List[float],
    start_row: int,
    end_row: int,
    total_rows: int,
    header_height_ratio: float = 0.08,
) -> List[float]:
    if not table_bbox or len(table_bbox) < 4:
        return [0.0, 0.0, 0.0, 0.0]

    x0, y0, x1, y1 = table_bbox
    total_height = y1 - y0

    header_height = total_height * header_height_ratio
    body_y_start = y0 + header_height
    body_height = max(0.0, total_height - header_height)

    row_height = body_height / max(total_rows, 1)

    # If this slice starts at row 0, include the header area
    if start_row == 0:
        slice_y0 = y0
    else:
        slice_y0 = body_y_start + (start_row * row_height)

    slice_y1 = body_y_start + (end_row * row_height)
    slice_y1 = min(slice_y1, y1)

    return [
        round(float(x0), 2),
        round(float(slice_y0), 2),
        round(float(x1), 2),
        round(float(slice_y1), 2),
    ]


def format_markdown_table(headers: List[str], rows: List[List[str]]) -> str:
    if not headers and not rows:
        return ""

    num_cols = len(headers) if headers else (max(len(r) for r in rows) if rows else 0)
    if num_cols == 0:
        return ""

    normalized_headers = headers + [""] * (num_cols - len(headers))
    separator = ["---"] * num_cols

    lines = [
        "| " + " | ".join(str(h).strip() for h in normalized_headers) + " |",
        "| " + " | ".join(separator) + " |",
    ]

    for row in rows:
        normalized_row = [str(c).strip() if c is not None else "" for c in row]
        normalized_row = normalized_row + [""] * (num_cols - len(normalized_row))
        lines.append("| " + " | ".join(normalized_row) + " |")

    return "\n".join(lines)


def chunk_single_table(
    table_item: Dict[str, Any],
    max_rows: int = 12,
    overlap_rows: int = 1,
) -> List[Dict[str, Any]]:

    metadata = table_item.get("metadata", {})
    headers = metadata.get("headers", [])
    rows = metadata.get("rows", [])
    all_cells = metadata.get("cells", [])
    total_rows = len(rows)

    # Case 1: Small/medium table stays completely intact
    if total_rows <= max_rows:
        return [
            {
                "page_number": table_item["page_number"],
                "type": "table",
                "content": table_item.get("content", ""),
                "bbox": table_item["bbox"],
                "metadata": {
                    "source_type": "table_intact",
                    "table_index": metadata.get("table_index", 0),
                    "total_rows": total_rows,
                    "is_slice": False,
                    "headers": headers,
                    "cells": all_cells,
                },
            }
        ]

    # Case 2: Large table -> Slice with row overlap and repeated headers
    chunks: List[Dict[str, Any]] = []
    start_idx = 0
    step = max(1, max_rows - overlap_rows)
    slice_counter = 0

    while start_idx < total_rows:
        end_idx = min(start_idx + max_rows, total_rows)
        row_slice = rows[start_idx:end_idx]

        slice_markdown = format_markdown_table(headers, row_slice)
        slice_bbox = compute_table_slice_bbox(
            table_bbox=table_item["bbox"],
            start_row=start_idx,
            end_row=end_idx,
            total_rows=total_rows,
        )

        # Filter cells that belong strictly to this row range (start_idx to end_idx - 1)
        slice_cells = [c for c in all_cells if start_idx <= c.get("row", -1) < end_idx]

        chunks.append(
            {
                "page_number": table_item["page_number"],
                "type": "table",
                "content": slice_markdown,
                "bbox": slice_bbox,
                "metadata": {
                    "source_type": "table_slice",
                    "table_index": metadata.get("table_index", 0),
                    "slice_index": slice_counter,
                    "row_range": [start_idx, end_idx - 1],
                    "total_rows": total_rows,
                    "is_slice": True,
                    "headers": headers,
                    "cells": slice_cells,
                },
            }
        )

        slice_counter += 1
        if end_idx >= total_rows:
            break

        start_idx += step

    return chunks


def chunk_table_items(
    items: List[Dict[str, Any]],
    max_rows: int = 12,
    overlap_rows: int = 1,
) -> List[Dict[str, Any]]:

    if not items:
        return []

    table_items = [it for it in items if it.get("type") == "table"]
    if not table_items:
        return []

    all_table_chunks: List[Dict[str, Any]] = []

    for tbl in table_items:
        sliced_chunks = chunk_single_table(
            table_item=tbl,
            max_rows=max_rows,
            overlap_rows=overlap_rows,
        )
        all_table_chunks.extend(sliced_chunks)

    return all_table_chunks
