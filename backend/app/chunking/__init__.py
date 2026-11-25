from typing import List, Dict, Any, Optional

from app.chunking.text_chunk import chunk_text_items
from app.chunking.scanned_text import chunk_scanned_items
from app.chunking.table_chunk import chunk_table_items
from app.chunking.image import chunk_image_items
from app.chunking.chart import chunk_chart_items


def chunk_document_items(
    extracted_items: List[Dict[str, Any]],
    pdf_source: Optional[Any] = None,
    max_text_words: int = 300,
    max_table_rows: int = 12,
    text_overlap_blocks: int = 1,
    table_overlap_rows: int = 1,
    ocr_confidence_threshold: float = 65.0,
) -> List[Dict[str, Any]]:

    if not extracted_items:
        return []

    all_chunks: List[Dict[str, Any]] = []

    # 1. Chunk Tables (handles large tables by slicing rows with repeated headers)
    table_chunks = chunk_table_items(
        items=extracted_items,
        max_rows=max_table_rows,
        overlap_rows=table_overlap_rows,
    )
    all_chunks.extend(table_chunks)

    # 2. Chunk Charts (1:1 standalone visual units)
    chart_chunks = chunk_chart_items(items=extracted_items)
    all_chunks.extend(chart_chunks)

    # 3. Chunk Images (1:1 standalone diagrams, decorative assets skipped)
    image_chunks = chunk_image_items(items=extracted_items, skip_decorative=True)
    all_chunks.extend(image_chunks)

    # 4. Chunk Narrative Text (page-aware grouping with block-level overlap + bbox union)
    text_chunks = chunk_text_items(
        items=extracted_items,
        max_words_per_chunk=max_text_words,
        overlap_blocks=text_overlap_blocks,
    )
    all_chunks.extend(text_chunks)

    # 5. Chunk Scanned / OCR Text (grouping with overlap + targeted VLM crop fallback)
    scanned_chunks = chunk_scanned_items(
        items=extracted_items,
        pdf_source=pdf_source,
        max_words_per_chunk=max_text_words,
        overlap_blocks=text_overlap_blocks,
        confidence_threshold=ocr_confidence_threshold,
    )
    all_chunks.extend(scanned_chunks)

    # Sort chunks by page_number, then by y0 coordinate for natural document order
    all_chunks.sort(key=lambda c: (c.get("page_number", 0), c.get("bbox", [0, 0])[1]))

    return all_chunks


# Backward compatibility alias
chunking = chunk_document_items
