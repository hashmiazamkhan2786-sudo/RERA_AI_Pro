#!/usr/bin/env python3
import sys
import subprocess
from pathlib import Path
import os
import shutil

PROJECT_ROOT = Path(__file__).parent.resolve()
BACKEND_DIR = PROJECT_ROOT / "backend"
FRONTEND_DIR = PROJECT_ROOT / "frontend"
JSON_DIR = PROJECT_ROOT / "jsons"
JSON_DIR.mkdir(exist_ok=True)

def run(cmd, label, cwd=None):
    print(f"\n▶ {label}")
    try:
        subprocess.run(cmd, check=True, cwd=cwd)
    except subprocess.CalledProcessError:
        print(f"❌ Pipeline failed at step: {label}")
        sys.exit(1)

def main():
    if len(sys.argv) != 2:
        print("Usage: python3 pipeline.py <RERA_PROJECT_URL>")
        sys.exit(1)
    rera_url = sys.argv[1]
    print("\n🚀 Starting RERA → Web pipeline")

    # Aggressive State Wipe: start run with a clean slate
    try:
        # Remove extracted_data.json if present
        extracted = JSON_DIR / "extracted_data.json"
        if extracted.exists():
            extracted.unlink()

        # Clear project-level download/temp directories if they exist
        for dname in (PROJECT_ROOT / "downloads", PROJECT_ROOT / "tmp", PROJECT_ROOT / "temp"):
            if dname.exists() and dname.is_dir():
                shutil.rmtree(dname, ignore_errors=True)
            # recreate empty directory to avoid downstream errors
            try:
                dname.mkdir(parents=True, exist_ok=True)
            except Exception:
                pass
    except Exception as e:
        print(f"Warning: failed to wipe state: {e}")

    # 1. Extract structure
    run([sys.executable, "extract_structure.py", rera_url], "Extracting structured project data", cwd=str(BACKEND_DIR))

    # 2. Extract doc text
    run([sys.executable, "extract_doc.py"], "Extracting document text (PDF / OCR)", cwd=str(BACKEND_DIR))

    # 3. Run Ollama AI Analysis
    run([sys.executable, "ollama_analyzer.py"], "Running Local AI Analysis (Ollama)", cwd=str(BACKEND_DIR))

    # 4. Rule-based risk rules
    run([sys.executable, "risk_rules.py"], "Applying rule-based risk checks", cwd=str(BACKEND_DIR))

    # 5. Pipeline complete
    print('\n✅ Pipeline complete! All JSON data saved. Run streamlit run app.py to view the UI.')

if __name__ == "__main__":
    main()