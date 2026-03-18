#!/usr/bin/env python3
import os
import sys
import json
from pathlib import Path
from playwright.sync_api import sync_playwright

# Resolve directories
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
JSON_DIR = PROJECT_ROOT / "jsons"
JSON_DIR.mkdir(exist_ok=True)

# ---------- same extraction helpers as before ----------
# (kept your original extraction logic, only file paths changed)

def extract_project_name(page):
    try:
        label = page.locator("div.col-md-4:has-text('Project Name')")
        value = label.locator("xpath=following-sibling::div[1]")
        name = value.inner_text(timeout=5000).strip()
        return name if name else "UNKNOWN PROJECT"
    except:
        return "UNKNOWN PROJECT"

def extract_sections(page):
    sections = []
    containers = page.locator("div.container")
    for i in range(containers.count()):
        container = containers.nth(i)
        title_loc = container.locator("div.h3.title")
        if title_loc.count() == 0:
            continue
        title = title_loc.first.inner_text().strip()
        box = container.locator("div.box")
        if box.count() == 0:
            continue
        fields = {}
        rows = box.locator("div.row")
        for r in range(rows.count()):
            row = rows.nth(r)
            cols = row.locator("div")
            if cols.count() < 2:
                continue
            key = cols.nth(0).inner_text().strip().rstrip(":")
            value = cols.nth(1).inner_text().strip()
            if key:
                fields[key] = value if value else None
        if fields:
            sections.append({"title": title, "fields": fields})
    return sections

def extract_apartments(page):
    apartments = []
    tables = page.locator("table")
    for i in range(tables.count()):
        table = tables.nth(i)
        headers = [h.inner_text().strip() for h in table.locator("th").all()]
        if "Unit Type" in headers and "Total Units" in headers:
            rows = table.locator("tbody tr")
            for r in range(rows.count()):
                cols = [c.inner_text().strip() for c in rows.nth(r).locator("td").all()]
                if len(cols) >= 7:
                    apartments.append({
                        "unit": cols[1],
                        "unit_type": cols[2],
                        "total_units": cols[3],
                        "remaining_units": cols[4],
                        "sold_units": cols[5],
                        "sold_last_quarter": cols[6]
                    })
            break
    return apartments

def extract_project_documents(page):
    documents = []
    table = page.locator("table.doc-table")
    if table.count() == 0:
        return documents
    rows = table.locator("tbody tr")
    for r in range(rows.count()):
        row = rows.nth(r)
        cols = row.locator("td")
        if cols.count() < 4:
            continue
        title = cols.nth(1).inner_text().strip()
        remarks_text = cols.nth(2).inner_text().strip()
        remarks = remarks_text if remarks_text else None
        links = cols.nth(3).locator("a")
        for i in range(links.count()):
            link = links.nth(i)
            href = link.get_attribute("href")
            tooltip = link.get_attribute("title")
            if href:
                documents.append({
                    "title": title,
                    "remarks": remarks,
                    "description": tooltip,
                    "url": href,
                    "category": "project",
                    "available": True
                })
    return documents

def extract_quarterly_documents(page):
    documents = []
    tables = page.locator("table")
    for i in range(tables.count()):
        table = tables.nth(i)
        headers = [h.inner_text().strip() for h in table.locator("th").all()]
        if "Engineer Certificate" in headers and "CA Certificate" in headers:
            rows = table.locator("tbody tr")
            for r in range(rows.count()):
                row = rows.nth(r)
                cols = row.locator("td")
                if cols.count() < 5:
                    continue
                quarter = cols.nth(1).inner_text().strip()
                doc_map = {
                    "Engineer Certificate": cols.nth(2),
                    "CA Certificate": cols.nth(3),
                    "Bank Statement": cols.nth(4)
                }
                for title, cell in doc_map.items():
                    link = cell.locator("a")
                    if link.count() > 0:
                        href = link.first.get_attribute("href")
                        if href:
                            documents.append({
                                "title": title,
                                "quarter": quarter,
                                "remarks": None,
                                "description": f"{title} for {quarter}",
                                "url": href,
                                "category": "quarterly",
                                "available": True
                            })
            break
    return documents

def extract(url):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        # Use a custom user agent to prevent bot blocking
        context = browser.new_context(user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        page = context.new_page()
        
        try:
            # wait_until='domcontentloaded' prevents timeouts from hanging 3rd party scripts over HTTP
            page.goto(url, timeout=120000, wait_until="domcontentloaded")
            # Wait 3 seconds for JS elements to render instead of networkidle which hangs on RERA
            page.wait_for_timeout(3000)
        except Exception as e:
            print(f"Warning on page load: {e}")
            # If it partially loaded but timed out, we can still try to extract
        
        project_docs = extract_project_documents(page)
        quarterly_docs = extract_quarterly_documents(page)
        data = {
            "project_name": extract_project_name(page),
            "sections": extract_sections(page),
            "apartments": extract_apartments(page),
            "documents": project_docs + quarterly_docs,
            "source_url": url
        }
        browser.close()
        return data

def run(url):
    data = extract(url)
    out = JSON_DIR / "structured_raw.json"
    with open(out, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    print(f"✅ Extracted: {data['project_name']}")
    print(f"📦 Sections: {len(data['sections'])}")
    print(f"🏢 Apartments: {len(data['apartments'])}")
    print(f"📄 Documents: {len(data['documents'])}")
    print(f"📝 Written to: {out}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python backend/extract_structure.py <url>")
        sys.exit(1)
    run(sys.argv[1])