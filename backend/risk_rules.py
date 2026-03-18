#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
JSON_DIR = PROJECT_ROOT / "jsons"
JSON_DIR.mkdir(exist_ok=True)

INPUT_FILE = JSON_DIR / "structured_raw.json"
OUTPUT_FILE = JSON_DIR / "risk_flags.json"

DATE_FORMATS = ["%d-%m-%Y", "%d %b %Y", "%Y-%m-%d"]
SEVERITY_MAP = {"HIGH": "red", "MEDIUM": "amber", "LOW": "green"}

def parse_date(value):
    if not value:
        return None
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt)
        except Exception:
            pass
    return None

def today():
    return datetime.today()

def rule_to_title(rule):
    return rule.replace("_", " ").title()

def why_it_matters(category):
    if category == "Compliance":
        return ("Mandatory regulatory documents are required to confirm legal compliance. Missing documents can delay possession or expose buyers to legal/financial risk.")
    if category == "Timeline":
        return ("Project delays increase uncertainty around possession timelines and may result in financial strain or extended waiting periods.")
    if category == "Inventory":
        return ("Lack of available units while a project is active may indicate data inconsistencies or limited buyer options.")
    return ("This issue may affect the reliability or transparency of the project.")

def check_project_delay(sections):
    risks = []
    info = next((s for s in sections if s.get("title") == "Project Information"), None)
    if not info:
        return risks
    fields = info.get("fields", {})
    end_date = parse_date(fields.get("Proposed End Date "))
    status = (fields.get("Construction Status ") or "").lower()
    if end_date and end_date < today() and "completed" not in status:
        risks.append({
            "severity": "HIGH",
            "category": "Timeline",
            "rule": "PROJECT_DELAYED",
            "message": "Project has crossed the proposed completion date but is still not marked as completed.",
            "evidence": {"proposed_end_date": end_date.strftime("%d-%m-%Y"), "current_status": status}
        })
    return risks

def check_flat_availability(apartments):
    risks = []
    total_remaining = 0
    parsed_any = False
    for unit in apartments:
        try:
            remaining = int(unit.get("remaining_units", 0))
            total_remaining += remaining
            parsed_any = True
        except Exception:
            continue
    if parsed_any and total_remaining == 0:
        risks.append({
            "severity": "MEDIUM",
            "category": "Inventory",
            "rule": "NO_FLATS_AVAILABLE",
            "message": "No flats are shown as available while the project is still active.",
            "evidence": {"remaining_units": 0}
        })
    return risks

def check_mandatory_documents(documents):
    risks = []
    required_docs = {
        "Engineer Certificate": ["engineer certificate"],
        "CA Certificate": ["ca certificate", "chartered accountant"],
        "Bank Certificate": ["bank certificate", "bank statement"]
    }
    available_titles = [d.get("title", "").lower() for d in documents if d.get("available") is True]
    for doc_name, keywords in required_docs.items():
        found = any(any(k in title for k in keywords) for title in available_titles)
        if not found:
            risks.append({
                "severity": "HIGH",
                "category": "Compliance",
                "rule": "MISSING_COMPLIANCE_DOCUMENT",
                "message": f"Mandatory compliance document not found: {doc_name}.",
                "evidence": doc_name
            })
    return risks

def normalize_risks(raw_risks):
    normalized = []
    for r in raw_risks:
        normalized.append({
            "level": SEVERITY_MAP.get(r.get("severity"), "amber"),
            "title": rule_to_title(r.get("rule", "Unknown Risk")),
            "summary": r.get("message", "Risk detected."),
            "why_it_matters": why_it_matters(r.get("category"))
        })
    return {"risk_flags": normalized}

def main():
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    raw_risks = []
    raw_risks += check_project_delay(data.get("sections", []))
    raw_risks += check_flat_availability(data.get("apartments", []))
    raw_risks += check_mandatory_documents(data.get("documents", []))
    normalized = normalize_risks(raw_risks)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(normalized, f, indent=2, ensure_ascii=False)
    print(f"🚨 Risk flags generated: {len(normalized['risk_flags'])}")
    for r in normalized["risk_flags"]:
        print(f"- [{r['level'].upper()}] {r['title']}")

if __name__ == "__main__":
    main()