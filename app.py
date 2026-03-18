import streamlit as st
import json
from pathlib import Path

# --- 1. SYSTEM CONFIGURATION ---
PROJECT_ROOT = Path(__file__).parent.resolve()
JSON_DIR = PROJECT_ROOT / "jsons"

st.set_page_config(page_title="RERA AI Multi-Audit Pro", layout="wide", initial_sidebar_state="collapsed")

# 🚀 NEW: Premium Light/Corporate Theme CSS (Separate Blocks Fix)
st.markdown("""
    <style>
    /* Force Light Background for the whole app */
    .stApp { background-color: #f8fafc !important; }
    .main .block-container { padding-top: 2rem; max-width: 1400px; }
    
    /* Left Column (AI Analysis) */
    .findings-container { max-height: 85vh; overflow-y: auto; padding-right: 15px; }
    .report-card { 
        background-color: #ffffff; 
        padding: 22px; 
        border-radius: 12px; 
        border-left: 6px solid #ef4444; /* Red Border */
        margin-bottom: 20px; 
        border-top: 1px solid #e2e8f0;
        border-right: 1px solid #e2e8f0;
        border-bottom: 1px solid #e2e8f0;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05); 
    }
    .report-card.green-card { border-left-color: #10b981; }
    .report-card.amber-card { border-left-color: #f59e0b; }
    
    .risk-title { font-weight: 800; font-size: 1.15rem; color: #0f172a; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;}
    .risk-detail { font-size: 0.95rem; color: #334155; margin-bottom: 15px; line-height: 1.6; }
    
    .why-box { 
        background-color: #f8fafc; 
        padding: 12px 16px; 
        border-radius: 8px; 
        font-size: 0.9rem; 
        color: #475569; 
        border-left: 3px solid #cbd5e1; 
    }
    
    /* Header Box */
    .project-info-header { 
        background: #ffffff; 
        padding: 20px 30px; 
        border-radius: 14px; 
        margin-bottom: 30px; 
        border: 1px solid #e2e8f0; 
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .project-name-header { font-size: 1.6rem; font-weight: 900; color: #0f172a; }
    
    .approved-badge { 
        background-color: #ecfdf5; 
        color: #059669; 
        padding: 8px 18px; 
        border-radius: 30px; 
        font-weight: 800; 
        font-size: 0.85rem; 
        border: 1px solid #34d399;
        letter-spacing: 0.5px;
    }
    
    /* Right Column (Separate Blocks UX) */
    .info-block { 
        background-color: #ffffff; 
        padding: 22px; 
        border-radius: 14px; 
        border: 1px solid #e2e8f0; 
        margin-bottom: 24px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
    }
    .section-title { 
        font-size: 1.1rem; 
        font-weight: 800; 
        color: #0f172a; 
        margin-top: 0px; 
        margin-bottom: 15px; 
        border-bottom: 2px solid #f1f5f9; 
        padding-bottom: 8px; 
        display: flex; 
        align-items: center; 
        gap: 8px; 
    }
    
    .info-row { 
        display: flex; 
        justify-content: space-between; 
        margin-bottom: 12px; 
        font-size: 0.9rem; 
        border-bottom: 1px dashed #e2e8f0; 
        padding-bottom: 8px; 
    }
    .info-row:last-child {
        border-bottom: none;
        margin-bottom: 0;
        padding-bottom: 0;
    }
    .info-label { color: #64748b; font-weight: 700; text-transform: uppercase; font-size: 0.75rem; letter-spacing: 0.5px; }
    .info-value { color: #0f172a; font-weight: 600; text-align: right; max-width: 65%; word-wrap: break-word; }
    
    /* Global Streamlit Text Overrides */
    h3 { color: #0f172a !important; font-weight: 900 !important; font-size: 1.4rem !important;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. LOAD DATA FROM JSON FILES ---
def load_project_data():
    """Load project details from extracted_data.json"""
    try:
        with open(JSON_DIR / "extracted_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def load_risk_data():
    """Load risk analysis from risk_flags_ai.json"""
    try:
        with open(JSON_DIR / "risk_flags_ai.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return None

def get_card_style(level):
    if level == "green": return "report-card green-card"
    elif level == "amber": return "report-card amber-card"
    else: return "report-card"

def get_emoji(level):
    if level == "green": return "🟢"
    elif level == "amber": return "🟡"
    else: return "🔴"

# --- 3. MAIN INTERFACE ---
project_data = load_project_data()
risk_data = load_risk_data()

if project_data is None or risk_data is None:
    st.warning("⚠️ **Data Files Not Found**")
    st.info("The automated pipeline has not been run yet. Please run your backend server and search from the portal.")
else:
    # --- Top Header ---
    project_name = project_data.get("project_name", "Unknown Project")
    st.markdown(
        f'<div class="project-info-header">'
        f'<div><div class="project-name-header">🏢 {project_name}</div>'
        f'<div style="color: #64748b; font-size: 0.95rem; margin-top: 6px; font-weight: 500;">Verified Property Intelligence & AI Analysis</div></div>'
        f'<div class="approved-badge">✔️ RERA APPROVED</div>'
        f'</div>', 
        unsafe_allow_html=True
    )

    # --- 2-Column Layout Creation (70% Left, 30% Right) ---
    col_left, col_right = st.columns([7, 3], gap="large")

    # ==========================================
    # LEFT COLUMN: AI ANALYSIS
    # ==========================================
    with col_left:
        st.markdown('<h3>🚩 Our AI Analysis</h3>', unsafe_allow_html=True)
        
        risk_flags = risk_data.get("risk_flags", [])
        
        if not risk_flags:
            st.info("✅ No risk flags detected in this project.")
        else:
            st.markdown('<div class="findings-container">', unsafe_allow_html=True)
            for item in risk_flags:
                level = item.get("level", "red")
                title = item.get("title", "Unknown Risk")
                summary = item.get("summary", "")
                why_matters = item.get("why_it_matters", "")
                
                style = get_card_style(level)
                emoji = get_emoji(level)
                
                summary_html = summary.replace('\n', '<br>').replace('"', '&quot;')
                why_matters_html = why_matters.replace('\n', '<br>').replace('"', '&quot;')
                
                # Zero indentation to prevent Streamlit from rendering as code blocks
                card_html = (
                    f'<div class="{style}">'
                    f'<div class="risk-title">{emoji} {title}</div>'
                    f'<div class="risk-detail">{summary_html}</div>'
                    f'<div class="why-box"><strong>Why this matters:</strong> {why_matters_html}</div>'
                    f'</div>'
                )
                st.markdown(card_html, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)

    # ==========================================
    # RIGHT COLUMN: PROJECT INFORMATION (Bhavya's Separate Blocks Update Fixed)
    # ==========================================
    with col_right:
        sections = project_data.get("sections", [])
        
        for section in sections:
            title = section.get("title", "")
            fields = section.get("fields", {})
            
            # Icons for different sections
            icon = "📄"
            if "Location" in title: icon = "📍"
            elif "Information" in title or "Details" in title: icon = "🏢"
            elif "Cost" in title or "Bank" in title or "Financial" in title: icon = "💰"
            
            # Zero indentation HTML string
            block_html = f'<div class="info-block"><div class="section-title">{icon} {title}</div>'
            
            has_valid_fields = False
            for key, value in fields.items():
                clean_key = key.strip()
                # Skip some empty or repetitive fields to keep it clean
                if value and str(value).lower() != "na" and str(value) != "-":
                    has_valid_fields = True
                    # Zero indentation HTML string concatenation
                    block_html += (
                        f'<div class="info-row">'
                        f'<span class="info-label">{clean_key}</span>'
                        f'<span class="info-value">{value}</span>'
                        f'</div>'
                    )
                    
            block_html += '</div>'
            
            # Only render this block if it actually contains data
            if has_valid_fields:
                st.markdown(block_html, unsafe_allow_html=True)