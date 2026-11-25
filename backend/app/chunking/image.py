from typing import List, Dict, Any


def chunk_image_items(
    items: List[Dict[str, Any]],
    skip_decorative: bool = True,
) -> List[Dict[str, Any]]:
    if not items:
        return []

    image_items = [it for it in items if it.get("type") == "image"]
    chunks: List[Dict[str, Any]] = []

    for img_idx, img in enumerate(image_items):
        content = img.get("content", "").strip()

        # Filter out purely decorative images if VLM identified them as such
        if skip_decorative and "[Decorative asset - no financial data]" in content:
            continue

        if not content:
            content = "[Visual Diagram / Corporate Asset]"

        meta = img.get("metadata", {})

        chunks.append(
            {
                "page_number": img["page_number"],
                "type": "image",
                "content": content,
                "bbox": img["bbox"],
                "metadata": {
                    "source_type": "visual_diagram",
                    "image_index": meta.get("image_index", img_idx),
                    "width": meta.get("width", 0),
                    "height": meta.get("height", 0),
                    "format": meta.get("format", "png"),
                },
            }
        )

    return chunks
