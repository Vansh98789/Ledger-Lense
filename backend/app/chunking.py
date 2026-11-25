from app.chunking import chunk_document_items


def chunk(extracted_items, pdf_source=None, **kwargs):
    return chunk_document_items(extracted_items, pdf_source=pdf_source, **kwargs)
