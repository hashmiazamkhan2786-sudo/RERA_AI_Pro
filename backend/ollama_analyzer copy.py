#!/usr/bin/env python3

import json
import requests
import re
from pathlib import Path


# =========================
# CONFIG
# =========================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
JSON_DIR = PROJECT_ROOT / "jsons"
JSON_DIR.mkdir(exist_ok=True)

INPUT_FILE = JSON_DIR / "extracted_data.json"
OUTPUT_FILE = JSON_DIR / "risk_flags_ai.json"

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"
TEMPERATURE = 0.0


# =========================
# UTILS
# =========================

def chunk_text(text, max_chars=8000, overlap=500):
    """
    Split long text into overlapping chunks.
    Prevents context loss.
    """
    chunks = []
    start = 0
    length = len(text)

    while start < length:
        end = start + max_chars
        chunk = text[start:end]
        chunks.append(chunk)
        start = end - overlap

    return chunks


def extract_json_array(raw_text):
    """
    Extract valid JSON array from messy LLM output.
    Handles markdown / extra text.
    """
    if not raw_text:
        return []

    # Remove markdown wrappers
    raw_text = raw_text.replace("```json", "")
    raw_text = raw_text.replace("```", "")
    raw_text = raw_text.strip()

    # Find first JSON array
    match = re.search(r'\[.*\]', raw_text, re.DOTALL)

    if not match:
        return []

    json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        return []


def deduplicate(results):
    """
    Remove duplicate findings from overlapping chunks.
    Ignores incorrectly formatted AI outputs.
    """
    seen = set()
    unique = []

    for item in results:
        # SUPER FIX: Check if item is actually a dictionary before processing
        if not isinstance(item, dict):
            continue 

        key = (
            item.get("title"),
            item.get("source_sentence")
        )

        if key not in seen:
            seen.add(key)
            unique.append(item)

    return unique


# =========================
# AI ANALYSIS
# =========================

def analyze_document(text):

    if not text:
        return []

    chunks = chunk_text(text)
    all_results = []

    print(f"  ➜ Split into {len(chunks)} chunks")

    # SUPER FIX: Added Critical Instruction to stop hallucination on RERA compliance
    base_prompt = '''You are a Real Estate Auditor. Extract ALL risks and positive flags from the text.

CRITICAL INSTRUCTION: Do NOT flag standard RERA compliance mandates (such as depositing 70% of funds in a separate bank account, requiring CA/Engineer/Architect certificates for withdrawal, or conducting annual audits) as financial risks, loans, or delays. These are mandatory legal compliances and must be treated as standard or positive flags, not risks.

CATEGORIES YOU MUST USE:
- Delayed Possession / Timeline Risk
- Missing Basic Amenities (Water, Electricity, Sewage)
- Missing Fire Safety or Environmental Clearances
- Land Mortgaged to Bank / Heavy Loans
- Unsold Flats Pledged / Mortgaged to Bank
- Discrepancy in Carpet Area or Total Land Area
- Developer Right to Escalate Prices / Hidden Charges
- Shareholding / Ownership Transfer Risks
- General Financial, Legal, or Operational Risk
- RERA Act Compliance & Registration Mentioned
- Fire Safety Systems Present / Approved
- Basic Amenities (Drinking Water, Sewage) Provided
- Prominent Consultants / Architects Officially Hired
- Clear Title / Absence of Encumbrances Explicitly Stated
- Other General Compliance or Project Approval

OUTPUT FORMAT: Return a valid JSON array of objects:
[
  {
    "title": "Exact category name from above",
    "severity": "Critical",
    "source_sentence": "Short quote from text",
    "description": "Detailed explanation",
    "why_this_matters": "Why investor should care"
  }
]
'''

    for i, chunk in enumerate(chunks, 1):

        print(f"    → Analyzing chunk {i}/{len(chunks)}")

        prompt = base_prompt + "\n\nTEXT TO ANALYZE:\n" + chunk

        payload = {
            "model": MODEL,
            "prompt": prompt,
            "temperature": TEMPERATURE,
            "stream": False,
            "format": "json"
        }

        try:
            # SUPER FIX: Timeout changed from 120 to 600 seconds
            response = requests.post(
                OLLAMA_URL,
                json=payload,
                timeout=600
            )

            response.raise_for_status()

            raw = response.json().get("response", "").strip()

            parsed = extract_json_array(raw)

            if parsed and isinstance(parsed, list):
                all_results.extend(parsed)
                print(f"      ✓ {len(parsed)} findings")
            else:
                print("      ⚠️ Empty / invalid output")

        except Exception as e:
            print(f"      ❌ Chunk error: {e}")
            continue

    # Remove duplicates from overlapping chunks
    all_results = deduplicate(all_results)

    print(f"  ✓ Total findings after cleanup: {len(all_results)}")

    return all_results


# =========================
# MAIN PIPELINE
# =========================

def main():

    try:
        with open(INPUT_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

    except FileNotFoundError:
        print(f"❌ Error: '{INPUT_FILE}' not found.")
        return


    documents = data.get("documents", [])
    all_analysis = []


    for doc in documents:

        text = doc.get("extracted_text", "").strip()

        if not text:
            continue

        title = doc.get("title", "Unknown")

        print(f"\n📄 Analyzing document: {title}")

        result = analyze_document(text)

        if not isinstance(result, list):
            continue

        for item in result:

            title_cat = item.get('title') or 'General Financial, Legal, or Operational Risk'
            severity = item.get('severity') or 'Medium'
            description = item.get('description') or 'Details extracted by AI.'
            why = item.get('why_this_matters') or 'Requires investor attention.'
            source = item.get('source_sentence') or 'Refer to document.'

            level = 'amber'

            if severity.lower() == 'critical':
                level = 'red'

            elif severity.lower() == 'positive':
                level = 'green'

            risk_flag = {
                "level": level,
                "title": title_cat,
                "summary": description,
                "why_it_matters": why,
                "confidence": "high",
                "triggered_by": ["ollama_ai"],
                "evidence": [source] if source else [],
                "document_type": title
            }

            all_analysis.append(risk_flag)


    output_data = {
        "risk_flags": all_analysis
    }


    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        json.dump(
            output_data,
            f,
            indent=4,
            ensure_ascii=False
        )


    print(f"\n✅ Analysis complete. Total findings saved: {len(all_analysis)}")



# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    main()