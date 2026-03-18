#!/usr/bin/env python3
import os
import sys
import json
import tempfile
import requests
import urllib3
import re
from pathlib import Path
from pypdf import PdfReader
import pdfplumber
from pdf2image import convert_from_path
import pytesseract
from pytesseract import TesseractError

# Resolve paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
JSON_DIR = PROJECT_ROOT / "jsons"
JSON_DIR.mkdir(exist_ok=True)

INPUT_FILE = JSON_DIR / "structured_raw.json"
OUTPUT_FILE = JSON_DIR / "extracted_data.json"

REQUEST_TIMEOUT = 30
MIN_TEXT_LENGTH = 200

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Hard blacklist for aggressive guillotine
BLACKLIST = ['e0iz', 'oxZ', 'Xokf', 'kkjk', 'vuq', 'izk', 'jkok', 'cid:', 'oaa', 'gq;s', 'Hkfwe', 'fodkl', 'fu;e', "n'kk"]

def is_gibberish_line(line: str) -> bool:
    """
    Determines if a line is likely OCR garbage based on multiple heuristics.
    """
    line = line.strip()
    if not line:
        return True  # Empty lines are not gibberish, but we'll handle them separately
    
    # Blacklist guillotine: lowercase substring check first (fast fail)
    low = line.lower()
    if 'cid:' in low:
        return True
    for b in BLACKLIST:
        if b.lower() in low:
            return True
    
    # Kruti Dev Pattern: Use regex to catch unnatural uppercase/lowercase mixing like [A-Za-z]{3,}[ZxX]{1,}[A-Za-z]{1,}.
    if re.search(r'[A-Za-z]{3,}[ZxX]{1,}[A-Za-z]{1,}', line):
        return True
    
    # Vowel Density: If a line has letters but the vowel ratio (vowels / total letters) is less than 20% (0.20), return True.
    letters = re.findall(r'[a-zA-Z]', line)
    if letters:
        vowels = re.findall(r'[aeiouAEIOU]', line)
        vowel_ratio = len(vowels) / len(letters)
        if vowel_ratio < 0.20:
            return True
    
    # Dictionary Check (Optional): Basic check for common English syllables or consonant clusters
    words = re.findall(r'\b\w+\b', line.lower())
    if words:
        # Simple heuristic: if more than half the words are consonant-heavy (e.g., no vowels or mostly consonants)
        gibberish_words = 0
        for word in words:
            word_letters = re.findall(r'[a-z]', word)
            if word_letters:
                word_vowels = re.findall(r'[aeiou]', word)
                if len(word_vowels) / len(word_letters) < 0.3:  # Stricter for words
                    gibberish_words += 1
        if gibberish_words / len(words) > 0.5:
            return True
    
    return False

def download_pdf(url: str, path: str) -> bool:
    try:
        response = requests.get(url, timeout=REQUEST_TIMEOUT, verify=False)
        response.raise_for_status()
        with open(path, "wb") as f:
            f.write(response.content)
        return True
    except Exception as e:
        print(f"   ❌ Download failed: {e}")
        return False

def extract_text_from_pdf(path: str) -> str:
    text_chunks = []
    try:
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_chunks.append(text)
    except Exception:
        pass
    return "\n".join(text_chunks).strip()

def extract_text_with_ocr(path: str) -> str:
    text_chunks = []
    try:
        images = convert_from_path(path)
        for image in images:
            try:
                text = pytesseract.image_to_string(image, lang="eng+hin")
            except TesseractError:
                text = pytesseract.image_to_string(image, lang="eng")
            if text:
                text_chunks.append(text)
    except Exception:
        pass
    return "\n".join(text_chunks).strip()

def process_documents():
    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        print(f"❌ Error: '{INPUT_FILE}' not found.")
        return

    print(f"🚀 Project Found: {data.get('project_name')}")
    documents = data.get("documents", [])
    print(f"📂 Total Documents Found: {len(documents)}")

    for index, doc in enumerate(documents):
        title = doc.get("title", "Unknown")
        category = (doc.get("category") or "").lower()
        url = doc.get("url")
        print(f"\n[{index + 1}] Processing: {title}")

        if category == "quarterly" or "quarter" in title.lower():
            print("   ⚠️ Skipped (Quarterly Compliance)")
            doc["extraction_status"] = "Skipped"
            continue

        if not url:
            print("   ❌ No URL found")
            doc["extraction_status"] = "Failed"
            continue

        with tempfile.TemporaryDirectory() as tmpdir:
            pdf_path = os.path.join(tmpdir, "document.pdf")
            if not download_pdf(url, pdf_path):
                doc["extraction_status"] = "Failed"
                continue

            text = extract_text_from_pdf(pdf_path)
            source = "pdf"
            if len(text) < MIN_TEXT_LENGTH:
                print("   🔄 Low text detected, running OCR...")
                text = extract_text_with_ocr(pdf_path)
                source = "ocr"

            if not text:
                print("   ❌ No text extracted")
                doc["extraction_status"] = "Failed"
                continue

            # Apply deterministic OCR quality gate: filter out gibberish lines
            lines = text.split('\n')
            clean_lines = [line for line in lines if not is_gibberish_line(line)]
            text = '\n'.join(clean_lines)

            doc["extracted_text"] = text
            doc["text_source"] = source
            doc["text_length"] = len(text)
            doc["extraction_status"] = "Success"
            print(f"   ✅ Extracted {len(text)} characters (source: {source})")

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    print("\n🎉 Extraction complete.")
    print(f"📁 Output written to: {OUTPUT_FILE}")

if __name__ == "__main__":
    process_documents()