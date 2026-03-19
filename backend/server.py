#!/usr/bin/env python3
import sys
import json
import subprocess
from pathlib import Path
import requests
import urllib3
from flask import Flask, request, jsonify, Response
import time
from flask_cors import CORS
from bs4 import BeautifulSoup

# Disable SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)
# Enable CORS so your React frontend can talk to this Flask backend
CORS(app)

PROJECT_ROOT = Path(__file__).parent.parent.resolve()
PIPELINE = PROJECT_ROOT / "pipeline.py"
RERA_URL = "https://www.rera.mp.gov.in/project-all-loop.php"

# ==========================================
# 1. BHAVYA'S LOGIC: Search Projects by Name
# ==========================================
def fetch_rera_data(search_query):
    params = {
        "show": 100,
        "pagenum": 1,
        "search_txt": search_query,
        "project_type_id": "",
        "search_dist": "",
        "search_tehs": ""
    }

    try:
        # Increased timeout to 60s because the RERA MP website is notoriously slow
        response = requests.get(RERA_URL, params=params, timeout=60, verify=False)
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        results = []
        rows = soup.find_all('tr')
        
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 5:
                project_name = cells[1].get_text(strip=True)
                promoter_name = cells[2].get_text(strip=True)
                district = cells[3].get_text(strip=True)
                status = cells[4].get_text(strip=True)
                
                link_tag = row.find('a', href=True)
                link = link_tag['href'] if link_tag else "#"
                
                # --- YAHAN FIX KIYA HAI (Taki har relative link pura ho jaye) ---
                if link != "#" and not link.startswith('http'):
                    link = f"https://www.rera.mp.gov.in/{link}"

                results.append({
                    "name": project_name,
                    "promoter": promoter_name,
                    "district": district,
                    "status": status,
                    "link": link
                })
        return results

    except Exception as e:
        print(f"Request Error: {e}")
        return []

@app.route('/search', methods=['POST'])
def search():
    query = request.json.get('query', '')
    if not query:
        return jsonify({"error": "No query provided"}), 400
    data = fetch_rera_data(query)
    return jsonify(data)


# ==========================================
# 2. YOUR LOGIC: Run AI Pipeline on the URL
# ==========================================
@app.route('/run_pipeline', methods=['GET'])
def run_pipeline():
    rera_url = request.args.get("url")
    if not rera_url:
        return jsonify({"error": "Missing RERA URL"}), 400

    print(f"\n⚙️ Triggering AI Pipeline for: {rera_url}")
    
    def generate():
        try:
            # Popen allows us to non-blockingly check if process is done
            process = subprocess.Popen([sys.executable, str(PIPELINE), rera_url])
            
            counter = 0
            while process.poll() is None:
                time.sleep(1)
                counter += 1
                if counter >= 10:
                    # Yield enough blank spaces to force network buffers to flush
                    # and keep the TCP connection alive under long AI runtimes
                    yield b" " * 1024
                    counter = 0
                    
            if process.returncode == 0:
                yield b'{"status": "success", "message": "Pipeline finished!"}'
            else:
                yield b'{"status": "error", "message": "Pipeline failed to execute"}'
        except Exception as e:
            print(f"❌ Pipeline crashed: {e}")
            yield b'{"status": "error", "message": "Exception occurred"}'

    return Response(generate(), mimetype='application/json')

# ==========================================
# 3. REPORT ENDPOINT: Serve AI Analysis JSON
# ==========================================
@app.route('/report', methods=['GET'])
def get_report():
    """Serve the AI analysis report as JSON for in-page rendering"""
    try:
        project_path = PROJECT_ROOT / "jsons" / "extracted_data.json"
        risks_path = PROJECT_ROOT / "jsons" / "risk_flags_ai.json"

        if not project_path.exists() or not risks_path.exists():
            return jsonify({"error": "Report not ready yet"}), 404

        with open(project_path, "r", encoding="utf-8") as f:
            project_data = json.load(f)
        with open(risks_path, "r", encoding="utf-8") as f:
            risk_data = json.load(f)

        return jsonify({
            "project": project_data,
            "risks": risk_data
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    print("🚀 Live Hybrid Server running on http://localhost:5000")
    # 🚀 SUPER FIX: Added use_reloader=False to prevent double processing & crashes!
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
