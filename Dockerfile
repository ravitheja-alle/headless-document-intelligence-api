# Use official lightweight Python image
FROM python:3.11-slim

# Working directory
WORKDIR /app

# Python settings
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Install OCR + PDF system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    tesseract-ocr \
    libgl1-mesa-glx \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Render provides dynamic PORT
ENV PORT=8000

EXPOSE $PORT

# Start FastAPI app
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}