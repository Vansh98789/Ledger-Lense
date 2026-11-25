# extract data from pdf --> clean data --> chunk it --> embedd it --> store it in vector db
from extract_data import extract_data
from typing import Union


# {
#                 "page_number": int,
#                 "type": "text" | "table" | "chart" | "image" | "scanned_text",
#                 "content": str (text or markdown representation),
#                 "bbox": [x0, y0, x1, y1],
#                 "metadata": dict (e.g. cell info, table index, OCR confidence)
#             },


def ingestion(pdf_source: Union[str, bytes, bytearray]):
    data = extract_data(pdf_source)
