from typing import List, Dict, Any


def chunk_chart_items(
    items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:

    if not items:
        return []

    chart_items = [it for it in items if it.get("type") == "chart"]
    chunks: List[Dict[str, Any]] = []

    for c_idx, chart in enumerate(chart_items):
        content = chart.get("content", "").strip()
        if not content:
            content = "[Financial Chart Region - Visual data omitted]"

        meta = chart.get("metadata", {})

        chunks.append(
            {
                "page_number": chart["page_number"],
                "type": "chart",
                "content": content,
                "bbox": chart["bbox"],
                "metadata": {
                    "source_type": "financial_chart",
                    "chart_index": meta.get("chart_index", c_idx),
                    "has_vlm_analysis": meta.get("has_vlm_analysis", False),
                },
            }
        )

    return chunks
