# ── Stage 1: build deps ───────────────────────────────────────────────────────
FROM python:3.13-slim AS builder

# Install uv for fast dependency resolution
RUN pip install --no-cache-dir uv

WORKDIR /app

# Copy dependency files only (layer cache: only re-runs when deps change)
COPY pyproject.toml uv.lock* ./

# Install all dependencies into /app/.venv
RUN uv sync --frozen --no-dev


# ── Stage 2: runtime ──────────────────────────────────────────────────────────
FROM python:3.13-slim

# Install Tesseract OCR binary (needed by pytesseract / scan_ocr_extract.py)
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       tesseract-ocr \
       tesseract-ocr-eng \
       libglib2.0-0 \
       libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the virtualenv built in stage 1
COPY --from=builder /app/.venv /app/.venv

# Copy application source
COPY . .

# Make sure venv is on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# Expose the port Uvicorn will listen on
EXPOSE 8000

# Health check for Docker / Render
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

# Start the server
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
