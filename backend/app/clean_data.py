from typing import Any, Dict, List


def _overlap_ratio(inner_bbox: List[float], outer_bbox: List[float]) -> float:
    if len(inner_bbox) != 4 or len(outer_bbox) != 4:
        return 0.0
    ix0 = max(inner_bbox[0], outer_bbox[0])
    iy0 = max(inner_bbox[1], outer_bbox[1])
    ix1 = min(inner_bbox[2], outer_bbox[2])
    iy1 = min(inner_bbox[3], outer_bbox[3])
    if ix1 <= ix0 or iy1 <= iy0:
        return 0.0
    inter_area = (ix1 - ix0) * (iy1 - iy0)
    inner_area = max(
        (inner_bbox[2] - inner_bbox[0]) * (inner_bbox[3] - inner_bbox[1]), 1e-6
    )
    return inter_area / inner_area


def clean_extracted_items(
    items: List[Dict[str, Any]],
    overlap_threshold: float = 0.7,
) -> List[Dict[str, Any]]:
    structured_bboxes: Dict[int, List[List[float]]] = {}
    for item in items:
        if item.get("type") in ("table", "chart", "image") and item.get("bbox"):
            structured_bboxes.setdefault(item["page_number"], []).append(item["bbox"])

    seen = set()
    cleaned: List[Dict[str, Any]] = []

    for item in items:
        norm = " ".join(item.get("content", "").split()).lower()
        if not norm:
            continue

        page = item.get("page_number", 0)
        item_type = item.get("type", "")

        if item_type == "text" and item.get("bbox"):
            if any(
                _overlap_ratio(item["bbox"], region) >= overlap_threshold
                for region in structured_bboxes.get(page, [])
            ):
                continue

        key = (page, item_type, norm)
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(item)

    return cleaned
