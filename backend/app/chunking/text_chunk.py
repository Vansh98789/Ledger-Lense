from typing import List, Dict, Any


def compute_bbox_union(bboxes: List[List[float]]) -> List[float]:

    if not bboxes:
        return [0.0, 0.0, 0.0, 0.0]

    min_x0 = min(b[0] for b in bboxes)
    min_y0 = min(b[1] for b in bboxes)
    max_x1 = max(b[2] for b in bboxes)
    max_y1 = max(b[3] for b in bboxes)

    return [round(min_x0, 2), round(min_y0, 2), round(max_x1, 2), round(max_y1, 2)]


def merge_text_block_group(
    group: List[Dict[str, Any]], page_number: int
) -> Dict[str, Any]:
    combined_text = "\n\n".join(b["content"] for b in group if b.get("content"))
    all_bboxes = [b["bbox"] for b in group if b.get("bbox")]
    union_bbox = compute_bbox_union(all_bboxes)

    block_indices = [
        b["metadata"]["block_index"]
        for b in group
        if "metadata" in b and "block_index" in b["metadata"]
    ]

    return {
        "page_number": page_number,
        "type": "text",
        "content": combined_text.strip(),
        "bbox": union_bbox,
        "metadata": {
            "source_type": "narrative_text",
            "block_count": len(group),
            "block_indices": block_indices,
            "word_count": len(combined_text.split()),
            "sub_bboxes": all_bboxes,
        },
    }


def chunk_text_items(
    items: List[Dict[str, Any]],
    max_words_per_chunk: int = 300,
    overlap_blocks: int = 1,
) -> List[Dict[str, Any]]:
    if not items:
        return []

    text_items = [it for it in items if it.get("type") == "text"]
    if not text_items:
        return []

    pages_dict: Dict[int, List[Dict[str, Any]]] = {}
    for item in text_items:
        p = item["page_number"]
        if p not in pages_dict:
            pages_dict[p] = []
        pages_dict[p].append(item)

    chunks: List[Dict[str, Any]] = []

    for page_num in sorted(pages_dict.keys()):
        page_blocks = pages_dict[page_num]

        current_group: List[Dict[str, Any]] = []
        current_words = 0

        for block in page_blocks:
            content = block.get("content", "")
            words_in_block = len(content.split())

            if current_words + words_in_block > max_words_per_chunk and current_group:
                chunks.append(merge_text_block_group(current_group, page_num))

                # Carry over trailing blocks for sliding window overlap
                if overlap_blocks > 0 and len(current_group) >= overlap_blocks:
                    overlap = current_group[-overlap_blocks:]
                else:
                    overlap = []

                current_group = list(overlap)
                current_words = sum(
                    len(b.get("content", "").split()) for b in current_group
                )

            current_group.append(block)
            current_words += words_in_block

        if current_group:
            chunks.append(merge_text_block_group(current_group, page_num))

    return chunks
