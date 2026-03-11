"""
app.py — Mobilitätsatlas Stormarn · Hauptdatei
Starten mit: streamlit run app.py
"""
import streamlit as st

st.set_page_config(
    page_title="Mobilitätsatlas Stormarn",
    page_icon="🚌",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── WAS Corporate CSS ─────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

  :root {
    --was-blue:   #003064;
    --was-orange: #f29400;
    --border:     #dde1e7;
    --surface:    #f0f2f5;
  }

  html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', sans-serif !important;
  }

  /* Header */
  [data-testid="stAppViewContainer"] > .main > div:first-child { padding-top: 0 !important; }
  header[data-testid="stHeader"] {
    background: #003064 !important;
    border-bottom: 4px solid #f29400;
  }
  header[data-testid="stHeader"] * { color: #fff !important; }

  /* Sidebar */
  [data-testid="stSidebar"] {
    background: #ffffff !important;
    border-right: 1px solid #dde1e7;
  }
  [data-testid="stSidebar"] .stSelectbox label,
  [data-testid="stSidebar"] .stTextInput label,
  [data-testid="stSidebar"] p {
    font-size: 12px !important;
    color: #6b7280 !important;
  }

  /* Metric cards */
  [data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #dde1e7;
    border-radius: 10px;
    padding: 12px 16px;
  }
  [data-testid="stMetricValue"] { font-family: 'IBM Plex Mono', monospace !important; }

  /* Buttons */
  .stButton > button {
    background: #003064 !important;
    color: #fff !important;
    border: none !important;
    border-radius: 7px !important;
    font-weight: 600 !important;
  }
  .stButton > button:hover { background: #00255a !important; }

  /* Tabs */
  .stTabs [data-baseweb="tab-list"] { border-bottom: 2px solid #dde1e7; }
  .stTabs [data-baseweb="tab"][aria-selected="true"] {
    color: #003064 !important;
    border-bottom: 3px solid #f29400 !important;
  }

  /* Orange accent bar at top of sidebar */
  .was-sidebar-header {
    background: #003064;
    color: white;
    padding: 16px 20px;
    margin: -1rem -1rem 1rem -1rem;
    border-bottom: 4px solid #f29400;
  }
  .was-eyebrow {
    font-size: 9px; font-weight: 700; letter-spacing: .14em;
    text-transform: uppercase; color: #f29400; margin-bottom: 4px;
  }
  .was-title { font-size: 17px; font-weight: 700; color: #fff; }
  .was-sub   { font-size: 10px; color: rgba(255,255,255,.55); margin-top:2px; }

  /* Status badges */
  .badge-grün   { background:#dcfce7; color:#16a34a; border:1px solid #86efac; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }
  .badge-gelb   { background:#fef9c3; color:#d97706; border:1px solid #fde047; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }
  .badge-rot    { background:#fee2e2; color:#dc2626; border:1px solid #fca5a5; border-radius:5px; padding:2px 8px; font-size:11px; font-weight:600; }

  /* GE-Karte */
  .ge-card {
    background: #fff; border: 1.5px solid #dde1e7; border-radius: 9px;
    padding: 12px 14px; margin-bottom: 8px; cursor: pointer;
    transition: border-color .15s;
  }
  .ge-card:hover { border-color: #f29400; }
  .ge-card-name  { font-weight: 700; font-size: 13px; color: #003064; }
  .ge-card-meta  { font-size: 11px; color: #6b7280; margin-top: 3px; }

  div[data-testid="stHorizontalBlock"] { gap: 8px; }
</style>
""", unsafe_allow_html=True)

# ── Navigation ────────────────────────────────────────────
pg = st.navigation([
    st.Page("pages/01_karte.py",      title="🗺 Karte",          default=True),
    st.Page("pages/02_analyse.py",    title="📊 Analyse"),
    st.Page("pages/03_feedback.py",   title="📋 Feedback"),
    st.Page("pages/04_massnahmen.py", title="⚡ Maßnahmen"),
    st.Page("pages/05_admin.py",      title="⚙ Admin"),
])
pg.run()
