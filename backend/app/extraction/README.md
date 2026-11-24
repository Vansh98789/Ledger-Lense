                     Raw PDF Page
                          │
         ┌────────────────┴────────────────┐
         │ 1. Is this a Scanned Page?      │
         │    (Text character count < 50)  │
         └────────────────┬────────────────┘
                 NO       │       YES
        ┌─────────────────┘       └─────────────────┐
        ▼                                           ▼
[Digital Extraction Path]                   [Full-Page OCR / VLM Path]
  Step 2: Detect & Extract Tables             (Tesseract OCR / Vision LLM)
          (pdfplumber / PyMuPDF)              Extracts text + tables visually
          └── Save table bboxes
                 │
  Step 3: Detect & Extract Charts/Figures
          (Vector graphics / Embedded images)
          └── Send crop to VLM for summary
          └── Save chart bboxes
                 │
  Step 4: Combine all bboxes into `ignore_rects`
          ignore_rects = table_bboxes + chart_bboxes + image_bboxes
                 │
  Step 5: Extract Narrative Text Blocks
          (PyMuPDF get_text("blocks"))
          └── Skip blocks inside ignore_rects
                 │
                 ▼
[ Unified Page Chunks with BBoxes ]





                           PDF Page
                              │
               Is word count < 50 words?
                              │
             ┌────────────────┴────────────────┐
            NO                                YES
             │                                 │
     [Digital Text Page]               [Scanned / Image Page]
  (Skip OCR, handled by               Renders page to 200 DPI image
   text_extract & table_extract)      Runs Tesseract image_to_data
                                               │
                                 Is average confidence >= 80%?
                                               │
                                 ┌─────────────┴─────────────┐
                                YES                         NO
                                 │                           │
                        [Tesseract Output]            [VLM Fallback]
                       High confidence OCR         Routes image to Groq VLM
                       with word/line bboxes       (llama-3.2-11b-vision-preview)
                       method: 'tesseract'         using prompts/v1/vlm_ocr_v1.txt
                                                   method: 'vlm_fallback'