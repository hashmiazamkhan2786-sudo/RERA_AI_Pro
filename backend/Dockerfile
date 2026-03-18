# Python ka base image
FROM python:3.10-slim

# Working directory set karo
WORKDIR /app

# OCR aur PDF processing ke liye zaroori system tools install karo (Ye bahut zaroori hai!)
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    poppler-utils \
    && rm -rf /var/lib/apt/lists/*

# Requirements copy aur install karo
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Baaki saara code container me copy karo
COPY . .