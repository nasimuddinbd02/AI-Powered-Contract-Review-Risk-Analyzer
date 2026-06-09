# ContractIQ backend image
FROM python:3.12-slim

WORKDIR /app

# System deps for PyMuPDF + OCR fallback (optional but supported).
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY contractiq ./contractiq
COPY pyproject.toml .

EXPOSE 8000
CMD ["uvicorn", "contractiq.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
