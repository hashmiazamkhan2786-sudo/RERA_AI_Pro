#!/usr/bin/env python3

import json
import os
import re
import time  # 👈 Yahan time import kiya hai
from pathlib import Path
from groq import Groq
from dotenv import load_dotenv

# Load environment variables (API Key)
load_dotenv()

# =========================
# CONFIG
# =========================

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
JSON_DIR = PROJECT_ROOT / "jsons"
JSON_DIR.mkdir(exist_ok=True)

INPUT_FILE = JSON_DIR / "extracted_data.json"
OUTPUT_FILE = JSON_DIR / "risk_flags_ai.json"

# Initialize Groq Client (It automatically picks up GROQ_API_KEY from .env)
client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

# Using Groq's blazing fast Llama 3 model
MODEL = "llama-3.1-8b-instant" 
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
    Extract valid JSON array from Groq output.
    Groq JSON mode returns an object, we need to extract the 'flags' array.
    """
    if not raw_text:
        return []

    # Remove markdown wrappers just in case
    raw_text = raw_text.replace("```json", "")
    raw_text = raw_text.replace("```", "")
    raw_text = raw_text.strip()

    try:
        parsed_data = json.loads(raw_text)
        # We instructed the AI to put the array inside a "flags" key
        return parsed_data.get("flags", [])
    except json.JSONDecodeError:
        print("      ⚠️ Failed to parse JSON from Groq")
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

    # 🚀 NEW FIX: Investor Focused Prompt (Top 5 Rule applied to save tokens)
    base_prompt = '''You are an elite Real Estate Auditor presenting to a VIP Investor. Extract ONLY the absolute most crucial risks and positive flags. DO NOT extract minor issues.

CRITICAL INSTRUCTION 1: Do NOT flag standard RERA compliance mandates (such as depositing 70% of funds in a separate bank account, requiring CA/Engineer/Architect certificates for withdrawal, or conducting annual audits) as financial risks, loans, or delays. These are mandatory legal compliances and must be treated as standard or positive flags, not risks.

CRITICAL INSTRUCTION 2: STRICT OUTPUT LIMIT
You must restrict your findings to a MAXIMUM of:
- 5 Critical (Red) Risks (e.g., Heavy loans, missing clearances, major delays).
- 5 Medium (Yellow) Risks (e.g., General operational risks, minor discrepancies).
- 5 Positive (Green) Flags (e.g., RERA compliant, basic amenities present).

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

OUTPUT FORMAT: Return a valid JSON object with a single key "flags" containing an array of objects:
{
  "flags": [
    {
      "title": "Exact category name from above",
      "severity": "Critical", // Strictly choose: Critical, Medium, or Positive
      "source_sentence": "Short quote from text",
      "description": "Detailed explanation",
      "why_this_matters": "Why investor should care"
    }
  ]
}
'''

    for i, chunk in enumerate(chunks, 1):

        print(f"    → Analyzing chunk {i}/{len(chunks)}")

        messages = [
            {"role": "system", "content": base_prompt},
            {"role": "user", "content": f"TEXT TO ANALYZE:\n{chunk}"}
        ]

        try:
            # GROQ API CALL with JSON mode enabled
            completion = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                temperature=TEMPERATURE,
                response_format={"type": "json_object"}
            )

            raw = completion.choices[0].message.content.strip()
            parsed = extract_json_array(raw)

            if parsed and isinstance(parsed, list):
                all_results.extend(parsed)
                print(f"      ✓ {len(parsed)} findings")
            else:
                print("      ⚠️ Empty / invalid output")

        except Exception as e:
            print(f"      ❌ Chunk error: {e}")
            pass 

        # 👈 YAHAN FIX KIYA HAI: Har chunk ke baad 12 second ka aaram (Rate Limit Protection)
        print("      ⏳ Rate limit se bachne ke liye 12 second ka wait...")
        time.sleep(12)


    # Remove duplicates from overlapping chunks
    all_results = deduplicate(all_results)

    print(f"  ✓ Total findings from this document: {len(all_results)}")

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
                "triggered_by": ["groq_ai"],
                "evidence": [source] if source else [],
                "document_type": title
            }

            all_analysis.append(risk_flag)


    # 🚀 NEW FIX: Strictly limit to Top 5 Red, Top 5 Amber, Top 5 Green for the whole project
    red_flags = [f for f in all_analysis if f["level"] == "red"]
    amber_flags = [f for f in all_analysis if f["level"] == "amber"]
    green_flags = [f for f in all_analysis if f["level"] == "green"]

    # Slice list to keep only the top 5 of each category
    final_flags = red_flags[:5] + amber_flags[:5] + green_flags[:5]

    output_data = {
        "risk_flags": final_flags
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:

        json.dump(
            output_data,
            f,
            indent=4,
            ensure_ascii=False
        )

    print(f"\n✅ Analysis complete. ✨ Filtered down to TOP {len(final_flags)} Investor Flags (Saved Tokens & Interface Clutter!)")


# =========================
# ENTRY
# =========================

if __name__ == "__main__":
    main()