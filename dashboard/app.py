"""
Module 8: Streamlit Dashboard
SignalSense AI — Market Radar + Deep Analysis + Agent Activity Log
Run with: streamlit run dashboard/app.py
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import time
from datetime import datetime

from data.database        import Database
from agents.orchestrator  import Orchestrator

# ── PAGE CONFIG ──────────────────────────────────────────
st.set_page_config(
    page_title="SignalSense AI",
    page_icon="📡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── COLOR PALETTE ────────────────────────────────────────
colors = {
    "bg_primary": "#1a1a2e",
    "bg_secondary": "#16213e",
    "bg_card": "#0f3460",
    "accent_purple": "#7c3aed",
    "accent_violet": "#a855f7",
    "accent_blue": "#3b82f6",
    "text_primary": "#ffffff",
    "text_secondary": "#94a3b8",
    "green": "#10b981",
    "amber": "#f59e0b",
    "red": "#ef4444",
}

# ── CUSTOM CSS — FULL OVERHAUL ───────────────────────────
st.markdown("""
<style>
  /* ── Fonts ─────────────────────────────────────── */
  @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

  html, body, [class*="css"] {
    font-family: 'Outfit', sans-serif;
  }

  /* ── Global Background ─────────────────────────── */
  .stApp {
    background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #1a1a2e 100%);
    color: #ffffff;
  }

  /* remove top whitespace while keeping sidebar functional */
  .block-container {
    padding-top: 1rem !important;
    margin-top: 0 !important;
  }
  header[data-testid="stHeader"] {
    background: transparent !important;
    backdrop-filter: none !important;
  }
  div[data-testid="stAppViewContainer"] {
    margin-top: 0 !important;
    padding-top: 0 !important;
  }
  div[data-testid="stAppViewBlockContainer"] {
    padding-top: 1rem !important;
    margin-top: 0 !important;
  }
  .appview-container {
    margin-top: 0 !important;
    padding-top: 0 !important;
  }
  html, body {
    margin: 0 !important;
    padding: 0 !important;
  }
  /* hide the top-right toolbar & orange decoration line, but keep sidebar toggle */
  div[data-testid="stToolbar"] {
    display: none !important;
  }
  div[data-testid="stDecoration"] {
    display: none !important;
  }
  div[data-testid="stStatusWidget"] {
    display: none !important;
  }
  /* ensure sidebar is ALWAYS visible & never collapses */
  [data-testid="stSidebar"] {
    width: 310px !important;
    min-width: 310px !important;
    background: #16213e !important;
    border-right: 1px solid rgba(124, 58, 237, 0.2) !important;
    transform: none !important;
    z-index: 999 !important;
    position: relative !important;
  }
  [data-testid="stSidebar"] > div {
    width: 310px !important;
    background: #16213e !important;
  }
  [data-testid="stSidebar"] [data-testid="stSidebarContent"] {
    background: #16213e !important;
  }
  /* hide collapse button — sidebar always stays open */
  [data-testid="stSidebarCollapseButton"],
  [data-testid="stSidebarNavCollapseButton"],
  button[kind="headerNoPadding"] {
    display: none !important;
  }
  /* if sidebar is collapsed, force it back open */
  [data-testid="stSidebar"][aria-expanded="false"] {
    width: 310px !important;
    min-width: 310px !important;
    transform: none !important;
    margin-left: 0 !important;
    display: block !important;
  }
  div[data-testid="stSidebar"] .stRadio > div > label {
    color: #f8fafc !important;
    font-weight: 600;
    padding: 8px 12px;
    border-radius: 10px;
    transition: all 0.3s ease;
  }
  div[data-testid="stSidebar"] .stRadio > div > label:hover {
    background: rgba(124, 58, 237, 0.15);
    color: #ffffff !important;
  }
  div[data-testid="stSidebar"] .stRadio > div > label[data-checked="true"],
  div[data-testid="stSidebar"] .stRadio > div [data-testid="stMarkdownContainer"] {
    color: #ffffff !important;
  }

  /* ── Buttons ───────────────────────────────────── */
  .stButton > button {
    background: linear-gradient(135deg, #7c3aed, #3b82f6) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 12px 28px !important;
    font-weight: 600 !important;
    font-family: 'Outfit', sans-serif !important;
    width: 100%;
    transition: all 0.3s ease !important;
    letter-spacing: 0.5px;
    text-transform: uppercase;
    font-size: 0.85rem !important;
  }
  .stButton > button:hover {
    background: linear-gradient(135deg, #6d28d9, #2563eb) !important;
    transform: translateY(-2px) !important;
    box-shadow: 0 0 20px rgba(124, 58, 237, 0.5),
                0 0 40px rgba(124, 58, 237, 0.2) !important;
  }
  .stButton > button:active {
    transform: translateY(0px) !important;
  }

  /* ── Inputs ────────────────────────────────────── */
  label[data-testid="stWidgetLabel"] p,
  div[data-testid="stMarkdownContainer"] p {
    color: #e2e8f0 !important;
    font-weight: 500 !important;
  }
  .stTextInput > div > div > input,
  .stSelectbox > div > div > div {
    background: rgba(124, 58, 237, 0.08) !important;
    border: 1px solid rgba(124, 58, 237, 0.3) !important;
    border-radius: 10px !important;
    color: #ffffff !important;
    font-family: 'Outfit', sans-serif !important;
  }
  .stTextInput > div > div > input:focus {
    border-color: #7c3aed !important;
    box-shadow: 0 0 12px rgba(124, 58, 237, 0.25) !important;
  }

  /* ── Slider ────────────────────────────────────── */
  .stSlider > div > div > div > div {
    background: #7c3aed !important;
  }

  /* ── Checkbox ──────────────────────────────────── */
  .stCheckbox label span {
    color: #e2e8f0 !important;
    font-weight: 500 !important;
  }

  /* ── Metric Cards (glassmorphism) ──────────────── */
  .glass-metric {
    background: rgba(124, 58, 237, 0.1);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 16px;
    padding: 24px 28px;
    margin-bottom: 14px;
    position: relative;
    overflow: hidden;
    transition: all 0.3s ease;
  }
  .glass-metric:hover {
    border-color: rgba(124, 58, 237, 0.4);
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.15);
    transform: translateY(-2px);
  }
  .glass-metric::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
    border-radius: 16px 16px 0 0;
  }
  .glass-metric .metric-value {
    font-size: 2.2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #a855f7, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    font-family: 'JetBrains Mono', monospace;
    line-height: 1.2;
  }
  .glass-metric .metric-value.green-val {
    background: linear-gradient(135deg, #10b981, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .glass-metric .metric-label {
    font-size: 0.72rem;
    color: #94a3b8;
    text-transform: uppercase;
    letter-spacing: 2px;
    margin-top: 6px;
    font-weight: 500;
  }
  .glass-metric .metric-glow {
    position: absolute;
    width: 120px;
    height: 120px;
    background: radial-gradient(circle, rgba(124, 58, 237, 0.15), transparent 70%);
    border-radius: 50%;
    top: -30px;
    right: -30px;
    pointer-events: none;
  }

  /* ── Signal Cards (glassmorphism) ──────────────── */
  .signal-card-glass {
    background: rgba(124, 58, 237, 0.06);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.15);
    border-radius: 16px;
    padding: 20px 24px;
    margin-bottom: 12px;
    border-left: 4px solid #3b82f6;
    transition: all 0.3s ease;
  }
  .signal-card-glass:hover {
    background: rgba(124, 58, 237, 0.12);
    border-color: rgba(124, 58, 237, 0.3);
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.1);
    transform: translateX(4px);
  }
  .signal-card-glass.buy   { border-left-color: #10b981; }
  .signal-card-glass.watch { border-left-color: #f59e0b; }
  .signal-card-glass.avoid { border-left-color: #ef4444; }

  .signal-stock-name {
    font-size: 1.15rem;
    font-weight: 700;
    color: #ffffff;
    font-family: 'Outfit', sans-serif;
  }

  /* ── Badges ────────────────────────────────────── */
  .badge {
    display: inline-block;
    padding: 4px 14px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
  }
  .badge-pattern {
    background: rgba(124, 58, 237, 0.2);
    color: #a855f7;
    border: 1px solid rgba(124, 58, 237, 0.3);
  }
  .badge-buy   { background: rgba(16, 185, 129, 0.15); color: #10b981; border: 1px solid rgba(16, 185, 129, 0.3); }
  .badge-watch { background: rgba(245, 158, 11, 0.15); color: #f59e0b; border: 1px solid rgba(245, 158, 11, 0.3); }
  .badge-avoid { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }
  .badge-bull  { background: rgba(59, 130, 246, 0.15); color: #3b82f6; border: 1px solid rgba(59, 130, 246, 0.3); }
  .badge-neutral { background: rgba(148, 163, 184, 0.15); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.3); }
  .badge-bear  { background: rgba(239, 68, 68, 0.15); color: #ef4444; border: 1px solid rgba(239, 68, 68, 0.3); }

  /* ── Confidence Bar ────────────────────────────── */
  .conf-bar-bg {
    background: rgba(124, 58, 237, 0.15);
    border-radius: 10px;
    height: 8px;
    width: 100%;
    overflow: hidden;
    margin-top: 4px;
  }
  .conf-bar-fill {
    height: 100%;
    border-radius: 10px;
    background: linear-gradient(90deg, #7c3aed, #3b82f6);
    transition: width 0.6s ease;
  }

  /* ── Section Title ─────────────────────────────── */
  .section-title {
    font-size: 1.15rem;
    font-weight: 700;
    color: #e2e8f0;
    border-bottom: 2px solid rgba(124, 58, 237, 0.3);
    padding-bottom: 10px;
    margin-bottom: 20px;
    font-family: 'Outfit', sans-serif;
  }

  /* ── Page Header ───────────────────────────────── */
  .page-header {
    font-family: 'Outfit', sans-serif;
    font-size: 2rem;
    font-weight: 800;
    background: linear-gradient(135deg, #a855f7, #3b82f6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 4px;
  }
  .page-subtitle {
    color: #94a3b8;
    font-size: 0.85rem;
    font-weight: 400;
    margin-bottom: 24px;
  }

  /* ── Activity Log (terminal-style) ─────────────── */
  .terminal-panel {
    background: #0a0a0f;
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 16px;
    padding: 20px 24px;
    max-height: 600px;
    overflow-y: auto;
    font-family: 'JetBrains Mono', monospace;
  }
  .terminal-header {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid rgba(124, 58, 237, 0.15);
  }
  .terminal-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #10b981;
    animation: blink-dot 1.5s ease-in-out infinite;
    box-shadow: 0 0 8px rgba(16, 185, 129, 0.5);
  }
  @keyframes blink-dot {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.3; }
  }
  .terminal-title {
    color: #10b981;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 2px;
    text-transform: uppercase;
  }
  .log-entry {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.78rem;
    padding: 6px 0;
    border-bottom: 1px solid rgba(124, 58, 237, 0.08);
    color: #94a3b8;
    line-height: 1.6;
  }
  .log-entry.INFO  { color: #94a3b8; }
  .log-entry.WARN  { color: #f59e0b; }
  .log-entry.ERROR { color: #ef4444; }

  /* ── Glass Card (reusable) ─────────────────────── */
  .glass-card {
    background: rgba(124, 58, 237, 0.1);
    backdrop-filter: blur(10px);
    -webkit-backdrop-filter: blur(10px);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 16px;
    padding: 24px;
    margin-bottom: 14px;
    transition: all 0.3s ease;
  }
  .glass-card:hover {
    border-color: rgba(124, 58, 237, 0.35);
    box-shadow: 0 8px 32px rgba(124, 58, 237, 0.12);
  }

  /* ── Insight Action Text ───────────────────────── */
  .action-buy {
    font-size: 1.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #10b981, #34d399);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .action-watch {
    font-size: 1.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #f59e0b, #fbbf24);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
  .action-avoid {
    font-size: 1.4rem;
    font-weight: 800;
    background: linear-gradient(135deg, #ef4444, #f87171);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }

  /* ── Streamlit overrides ───────────────────────── */
  .stExpander {
    border: 1px solid rgba(124, 58, 237, 0.2) !important;
    border-radius: 16px !important;
    background: rgba(124, 58, 237, 0.05) !important;
  }
  .stExpander > div > div {
    color: #e2e8f0 !important;
  }
  .stProgress > div > div > div > div {
    background: linear-gradient(90deg, #7c3aed, #3b82f6) !important;
  }
  div[data-testid="stMetric"] {
    background: rgba(124, 58, 237, 0.08);
    border: 1px solid rgba(124, 58, 237, 0.2);
    border-radius: 12px;
    padding: 12px 16px;
  }
  div[data-testid="stMetric"] label {
    color: #94a3b8 !important;
  }
  div[data-testid="stMetric"] [data-testid="stMetricValue"] {
    color: #a855f7 !important;
    font-family: 'JetBrains Mono', monospace !important;
  }

  /* ── Scrollbar ─────────────────────────────────── */
  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: #1a1a2e; }
  ::-webkit-scrollbar-thumb { background: rgba(124, 58, 237, 0.4); border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(124, 58, 237, 0.6); }

  /* ── Divider override ──────────────────────────── */
  hr { border-color: rgba(124, 58, 237, 0.15) !important; }

  /* ── Tables ────────────────────────────────────── */
  .stDataFrame, .stTable {
    background: rgba(124, 58, 237, 0.05) !important;
    border-radius: 12px;
  }
  table { background: transparent !important; }
  table tr { background: rgba(15, 23, 42, 0.6) !important; }
  table tr:hover { background: rgba(124, 58, 237, 0.15) !important; }
  table th { background: rgba(124, 58, 237, 0.2) !important; color: #a855f7 !important; }
  table td { color: #e2e8f0 !important; border-bottom: 1px solid rgba(124, 58, 237, 0.1) !important; }

  /* ── Sidebar stats ─────────────────────────────── */
  .sidebar-stat {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 8px 0;
    border-bottom: 1px solid rgba(124, 58, 237, 0.1);
  }
  .sidebar-stat-label {
    color: #e2e8f0;
    font-size: 0.85rem;
    font-weight: 500;
  }
  .sidebar-stat-value {
    color: #a855f7;
    font-family: 'JetBrains Mono', monospace;
    font-weight: 600;
    font-size: 0.9rem;
  }

  /* ── Footer ────────────────────────────────────── */
  .footer-text {
    text-align: center;
    color: rgba(148, 163, 184, 0.5);
    font-size: 0.72rem;
    letter-spacing: 1px;
    padding: 20px 0;
  }
</style>
""", unsafe_allow_html=True)

# ── INIT ─────────────────────────────────────────────────
@st.cache_resource
def get_db():
    return Database()

@st.cache_resource
def get_orchestrator():
    return Orchestrator()

db   = get_db()
orch = get_orchestrator()

# ── SIDEBAR ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style='text-align:center; padding: 16px 0 8px 0;'>
        <div style='font-size:2rem; margin-bottom:4px;'>📡</div>
        <div style='font-family:Outfit,sans-serif; font-size:1.3rem; font-weight:800;
            background: linear-gradient(135deg, #a855f7, #3b82f6);
            -webkit-background-clip:text; -webkit-text-fill-color:transparent;
            background-clip:text;'>SignalSense AI</div>
        <div style='color:#94a3b8; font-size:0.75rem; letter-spacing:2px; text-transform:uppercase;
            margin-top:4px;'>Autonomous Stock Intelligence</div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    page = st.radio("Navigate", ["🏠 Market Radar", "🔬 Deep Analysis", "📋 Activity Log", "💼 Portfolio Simulator"])
    st.divider()

    st.markdown("""
    <div style='color:#a855f7; font-size:0.7rem; letter-spacing:2px; text-transform:uppercase;
        font-weight:600; margin-bottom:12px;'>⚡ RUN PIPELINE</div>
    """, unsafe_allow_html=True)
    symbols_input = st.text_input("Symbols (comma-separated)", placeholder="RELIANCE,TCS,INFY")
    force_refresh = st.checkbox("Force refresh data")

    if st.button("🚀 Scan Market"):
        syms = [s.strip().upper() for s in symbols_input.split(",")] if symbols_input else None

        # ── Live Scan Execution ──────────────────────────
        progress_container = st.empty()
        log_container = st.empty()

        with progress_container.container():
            st.markdown("""
            <div style='background:rgba(124,58,237,0.1);border:1px solid rgba(124,58,237,0.3);
            border-radius:12px;padding:20px;'>
            <div style='color:#a855f7;font-size:0.75rem;letter-spacing:2px;margin-bottom:8px;
                text-transform:uppercase;font-weight:600;'>
            SCANNING IN PROGRESS</div>
            <div style='color:white;font-size:1rem;font-weight:600;margin-bottom:12px;
                font-family:Outfit,sans-serif;'>
            ⚙️ Running Live Pipeline...</div>
            </div>
            """, unsafe_allow_html=True)

        class StreamlitRedirect:
            def __init__(self, container):
                self.container = container
                self.logs = []
                self.buffer = ""
                self.orig_stdout = sys.stdout

            def write(self, data):
                self.orig_stdout.write(data)
                self.buffer += data
                while "\n" in self.buffer:
                    line, self.buffer = self.buffer.split("\n", 1)
                    if line.strip():
                        self.logs.append(line.strip())
                        if len(self.logs) > 30:
                            self.logs.pop(0)
                        self.container.code("\n".join(self.logs), language="bash")

            def flush(self):
                self.orig_stdout.flush()

        import sys
        redirector = StreamlitRedirect(log_container)
        
        try:
            sys.stdout = redirector
            orch.run(symbols=syms, force=force_refresh)
        finally:
            sys.stdout = redirector.orig_stdout

        # Complete
        with progress_container.container():
            st.markdown("""
            <div style='background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);
            border-radius:12px;padding:20px;'>
            <div style='color:#10b981;font-size:1rem;font-weight:700;font-family:Outfit,sans-serif;'>
            ✅ Pipeline Complete!</div>
            </div>
            """, unsafe_allow_html=True)
            
        import time
        time.sleep(1.5)
        st.rerun()

    st.divider()
    stats = db.get_stats()
    st.markdown(f"""
    <div style='padding:4px 0;'>
        <div class='sidebar-stat'>
            <span class='sidebar-stat-label'>Stocks Tracked</span>
            <span class='sidebar-stat-value'>{stats.get('stocks_tracked', 0)}</span>
        </div>
        <div class='sidebar-stat'>
            <span class='sidebar-stat-label'>Total Signals</span>
            <span class='sidebar-stat-value'>{stats.get('total_signals', 0)}</span>
        </div>
        <div class='sidebar-stat'>
            <span class='sidebar-stat-label'>Today's Signals</span>
            <span class='sidebar-stat-value'>{stats.get('today_signals', 0)}</span>
        </div>
        <div class='sidebar-stat' style='border-bottom:none;'>
            <span class='sidebar-stat-label'>Avg Win Rate</span>
            <span class='sidebar-stat-value'>{stats.get('avg_win_rate', 0)}%</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════
# PAGE 1: MARKET RADAR
# ══════════════════════════════════════════════════════════
if "Market Radar" in page:
    st.markdown("""
    <div class='page-header'>📡 Market Radar</div>
    <div class='page-subtitle'>Real-time signal intelligence · Last updated: """ +
    datetime.now().strftime('%d %b %Y, %H:%M') + """</div>
    """, unsafe_allow_html=True)

    radar = db.get_market_radar()

    if radar.empty:
        st.markdown("""
        <div class='glass-card' style='text-align:center; padding:60px 40px;'>
            <div style='font-size:3rem; margin-bottom:16px;'>📡</div>
            <div style='color:#e2e8f0; font-size:1.1rem; font-weight:600; margin-bottom:8px;'>
            No signals detected yet</div>
            <div style='color:#94a3b8; font-size:0.85rem;'>
            Run the pipeline from the sidebar to start scanning the market.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # ── TOP STATS ROW ────────────────────────────────
        c1, c2, c3, c4 = st.columns(4)
        with c1:
            st.markdown(f"""<div class="glass-metric">
                <div class="metric-glow"></div>
                <div class="metric-value">{len(radar)}</div>
                <div class="metric-label">Active Signals</div>
            </div>""", unsafe_allow_html=True)
        with c2:
            buys = len(radar[radar.get("suggested_action", pd.Series()) == "Buy"]) if "suggested_action" in radar else 0
            st.markdown(f"""<div class="glass-metric">
                <div class="metric-glow"></div>
                <div class="metric-value green-val">{buys}</div>
                <div class="metric-label">Buy Signals</div>
            </div>""", unsafe_allow_html=True)
        with c3:
            avg_conf = radar["confidence"].mean() if "confidence" in radar else 0
            st.markdown(f"""<div class="glass-metric">
                <div class="metric-glow"></div>
                <div class="metric-value">{avg_conf:.1f}%</div>
                <div class="metric-label">Avg Confidence</div>
            </div>""", unsafe_allow_html=True)
        with c4:
            avg_wr = radar["win_rate"].mean() if "win_rate" in radar else 0
            st.markdown(f"""<div class="glass-metric">
                <div class="metric-glow"></div>
                <div class="metric-value">{avg_wr:.1f}%</div>
                <div class="metric-label">Avg Win Rate</div>
            </div>""", unsafe_allow_html=True)

        st.divider()

        # ── FILTERS ──────────────────────────────────────
        col_f1, col_f2, col_f3 = st.columns(3)
        with col_f1:
            pat_filter = st.multiselect("Pattern", radar["pattern"].unique().tolist() if "pattern" in radar else [])
        with col_f2:
            act_filter = st.multiselect("Action", ["Buy","Watch","Avoid"])
        with col_f3:
            min_conf   = st.slider("Min Confidence %", 50, 100, 60)

        filtered = radar.copy()
        if pat_filter:
            filtered = filtered[filtered["pattern"].isin(pat_filter)]
        if act_filter and "suggested_action" in filtered:
            filtered = filtered[filtered["suggested_action"].isin(act_filter)]
        if "confidence" in filtered.columns:
            filtered["confidence"] = pd.to_numeric(filtered["confidence"], errors="coerce").fillna(0)
            filtered = filtered[filtered["confidence"] >= min_conf]

        # ── SIGNAL CARDS ─────────────────────────────────
        st.markdown(f'<div class="section-title">Signal Feed — {len(filtered)} results</div>',
                    unsafe_allow_html=True)

        for _, row in filtered.head(30).iterrows():
            action   = str(row.get("suggested_action", "Watch"))
            css_cls  = action.lower()
            badge_cls= f"badge-{css_cls}"
            wr_str   = f"{row['win_rate']:.1f}%" if pd.notna(row.get("win_rate")) else "N/A"
            ar_str   = f"{row['avg_return']:.2f}%" if pd.notna(row.get("avg_return")) else "N/A"
            conf_val = row.get('confidence', 0)
            conf_pct = min(max(float(conf_val), 0), 100)

            sentiment = str(row.get('sentiment', 'Neutral'))
            sent_cls = "badge-bull"
            if sentiment.lower() in ["bearish", "bear"]:
                sent_cls = "badge-bear"
            elif sentiment.lower() == "neutral":
                sent_cls = "badge-neutral"

            st.markdown(f"""
            <div class="signal-card-glass {css_cls}">
              <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:8px;">
                <div>
                  <span class="signal-stock-name">{row.get('symbol','')}</span>
                  &nbsp;<span class="badge badge-pattern">{row.get('pattern','')}</span>
                </div>
                <div style="display:flex; gap:6px; flex-wrap:wrap;">
                  <span class="badge {badge_cls}">{action}</span>
                  <span class="badge {sent_cls}">{sentiment}</span>
                </div>
              </div>
              <div style="margin-top:12px;">
                <div style="display:flex; align-items:center; gap:8px; margin-bottom:6px;">
                  <span style="color:#94a3b8; font-size:0.78rem;">Confidence</span>
                  <span style="color:#a855f7; font-family:'JetBrains Mono',monospace; font-weight:600; font-size:0.85rem;">{conf_pct:.1f}%</span>
                </div>
                <div class="conf-bar-bg">
                  <div class="conf-bar-fill" style="width:{conf_pct}%"></div>
                </div>
              </div>
              <div style="margin-top:12px; font-size:0.82rem; color:#94a3b8; display:flex; gap:20px; flex-wrap:wrap;">
                <span>📊 Win Rate: <strong style="color:#e2e8f0; font-family:'JetBrains Mono',monospace;">{wr_str}</strong></span>
                <span>💹 Avg Return: <strong style="color:#10b981; font-family:'JetBrains Mono',monospace;">{ar_str}</strong></span>
                <span>📅 {row.get('date','')}</span>
              </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ── PATTERN DISTRIBUTION CHART ────────────────────
        if "pattern" in radar.columns:
            pat_counts = radar["pattern"].value_counts().reset_index()
            pat_counts.columns = ["Pattern","Count"]
            fig = px.bar(
                pat_counts, x="Pattern", y="Count",
                color="Count",
                color_continuous_scale=[[0, "#7c3aed"], [0.5, "#a855f7"], [1, "#3b82f6"]],
                template="plotly_dark",
                title="Pattern Distribution"
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                showlegend=False,
                font=dict(family="Outfit, sans-serif", color="#94a3b8"),
                title_font=dict(family="Outfit, sans-serif", color="#e2e8f0", size=16),
                xaxis=dict(gridcolor="rgba(124,58,237,0.1)"),
                yaxis=dict(gridcolor="rgba(124,58,237,0.1)"),
            )
            fig.update_traces(
                marker_line_width=0,
                marker_cornerradius=8,
            )
            st.plotly_chart(fig, width="stretch")


# ══════════════════════════════════════════════════════════
# PAGE 2: DEEP ANALYSIS
# ══════════════════════════════════════════════════════════
elif "Deep Analysis" in page:
    st.markdown("""
    <div class='page-header'>🔬 Stock Deep Analysis</div>
    <div class='page-subtitle'>In-depth technical analysis with AI-powered insights</div>
    """, unsafe_allow_html=True)

    all_syms = db.get_all_symbols()

    col_s1, col_s2 = st.columns([2, 1])
    with col_s1:
        symbol = st.selectbox("Select Stock", options=all_syms if all_syms else ["RELIANCE"])
    with col_s2:
        st.markdown("<div style='margin-top:26px'></div>", unsafe_allow_html=True)
        if st.button("🔍 Scan This Stock"):
            with st.spinner(f"Scanning {symbol}..."):
                orch.scan_single(symbol)
            st.success("Done!")
            st.rerun()

    if symbol:
        # ── PRICE CHART ──────────────────────────────────
        df = db.get_ohlcv(symbol, days=365)
        if not df.empty:
            fig = go.Figure()

            # Candlestick
            fig.add_trace(go.Candlestick(
                x=df["date"],
                open=df["open"],
                high=df["high"],
                low=df["low"],
                close=df["close"],
                name=symbol,
                increasing=dict(
                    line=dict(color="#10b981", width=1),
                    fillcolor="#10b981"
                ),
                decreasing=dict(
                    line=dict(color="#ef4444", width=1),
                    fillcolor="#ef4444"
                ),
            ))

            # SMA10 overlay
            if len(df) >= 10:
                df["sma10"] = df["close"].rolling(10).mean()
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df["sma10"],
                    name="SMA 10",
                    line=dict(color="#a855f7", width=1.5, dash="dot"),
                ))

            # SMA30 overlay
            if len(df) >= 30:
                df["sma30"] = df["close"].rolling(30).mean()
                fig.add_trace(go.Scatter(
                    x=df["date"], y=df["sma30"],
                    name="SMA 30",
                    line=dict(color="#3b82f6", width=1.5, dash="dot"),
                ))

            # Signal markers — vertical dashed lines with annotation
            signals = db.get_signals(symbol=symbol)
            if not signals.empty:
                for _, sig in signals.iterrows():
                    sig_date = str(sig["date"])[:10]
                    fig.add_vline(
                        x=sig_date,
                        line_dash="dash",
                        line_color="#f59e0b",
                        line_width=1.5,
                    )
                    # Find matching row for annotation y-position
                    sig_df = df[df["date"].astype(str).str[:10] == sig_date]
                    y_pos = sig_df["high"].iloc[0] if not sig_df.empty else df["high"].max()
                    fig.add_annotation(
                        x=sig_date,
                        y=y_pos,
                        text=sig["pattern"],
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#f59e0b",
                        font=dict(color="#f59e0b", size=10),
                        bgcolor="rgba(245,158,11,0.15)",
                        bordercolor="rgba(245,158,11,0.3)",
                        borderwidth=1,
                        borderpad=4,
                    )

            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="#0f172a",
                plot_bgcolor="#0f172a",
                font=dict(family="JetBrains Mono, monospace", color="#94a3b8"),
                title=dict(
                    text=f"{symbol} — Candlestick Chart (1 Year)",
                    font=dict(size=16, color="#ffffff", family="Outfit, sans-serif")
                ),
                xaxis=dict(
                    rangeslider=dict(visible=False),
                    gridcolor="rgba(255,255,255,0.05)",
                    showgrid=True,
                    type="date",
                ),
                yaxis=dict(
                    gridcolor="rgba(255,255,255,0.05)",
                    showgrid=True,
                    tickprefix="₹",
                    tickformat=",.0f",
                ),
                legend=dict(
                    orientation="h",
                    yanchor="bottom", y=1.02,
                    xanchor="right", x=1,
                    bgcolor="rgba(0,0,0,0)",
                    font=dict(size=11)
                ),
                height=480,
                margin=dict(l=10, r=10, t=60, b=10),
                hovermode="x unified",
            )

            # Volume bar chart below
            if "volume" in df.columns and df["volume"].notna().any():
                fig.add_trace(go.Bar(
                    x=df["date"],
                    y=df["volume"],
                    name="Volume",
                    marker_color=[
                        "#10b981" if df["close"].iloc[i] >= df["open"].iloc[i]
                        else "#ef4444"
                        for i in range(len(df))
                    ],
                    yaxis="y2",
                    opacity=0.4,
                ))

                fig.update_layout(
                    yaxis2=dict(
                        overlaying="y",
                        side="right",
                        showgrid=False,
                        showticklabels=False,
                        range=[0, df["volume"].max() * 5],
                    )
                )

            st.plotly_chart(fig, width="stretch")
        else:
            st.warning(f"No price data for {symbol}. Run the pipeline first.")

        # ── SIGNALS + INSIGHTS ────────────────────────────
        signals = db.get_signals(symbol=symbol)
        if not signals.empty:
            st.markdown(f'<div class="section-title">Detected Signals & AI Insights</div>',
                        unsafe_allow_html=True)

            for _, sig in signals.iterrows():
                pattern = sig["pattern"]
                date    = str(sig["date"])[:10]
                bt      = db.get_backtest(symbol, pattern)
                ins     = db.get_insight(symbol, pattern, date)

                with st.expander(f"📌 {pattern} — {date} | Confidence: {sig['confidence']}%"):
                    c1, c2 = st.columns(2)

                    with c1:
                        st.markdown("#### 📊 Backtest Metrics")
                        if bt:
                            # Glass cards for metrics
                            st.markdown(f"""
                            <div class='glass-card'>
                                <div style='display:grid; grid-template-columns:1fr 1fr; gap:16px;'>
                                    <div>
                                        <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                            letter-spacing:1px; margin-bottom:4px;'>Win Rate</div>
                                        <div style='color:#10b981; font-size:1.5rem; font-weight:700;
                                            font-family:"JetBrains Mono",monospace;'>{bt.get('win_rate',0):.1f}%</div>
                                    </div>
                                    <div>
                                        <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                            letter-spacing:1px; margin-bottom:4px;'>Avg Return</div>
                                        <div style='color:#3b82f6; font-size:1.5rem; font-weight:700;
                                            font-family:"JetBrains Mono",monospace;'>{bt.get('avg_return',0):.2f}%</div>
                                    </div>
                                    <div>
                                        <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                            letter-spacing:1px; margin-bottom:4px;'>Max Drawdown</div>
                                        <div style='color:#ef4444; font-size:1.5rem; font-weight:700;
                                            font-family:"JetBrains Mono",monospace;'>{bt.get('max_drawdown',0):.1f}%</div>
                                    </div>
                                    <div>
                                        <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                            letter-spacing:1px; margin-bottom:4px;'>Risk/Reward</div>
                                        <div style='color:#a855f7; font-size:1.5rem; font-weight:700;
                                            font-family:"JetBrains Mono",monospace;'>{bt.get('risk_reward',0):.2f}x</div>
                                    </div>
                                </div>
                                <div style='margin-top:12px; padding-top:12px; border-top:1px solid rgba(124,58,237,0.15);
                                    color:#64748b; font-size:0.78rem;'>
                                    Based on {bt.get('total_occurrences',0)} historical occurrences
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("No backtest data yet.")

                    with c2:
                        st.markdown("#### 🤖 AI Insight")
                        if ins:
                            action = ins.get("suggested_action","Watch")
                            action_cls = f"action-{action.lower()}" if action.lower() in ["buy","watch","avoid"] else "action-watch"
                            sentiment = ins.get('sentiment','')
                            horizon = ins.get('time_horizon','')
                            summary = ins.get("summary","")
                            risk = ins.get('key_risk','')

                            st.markdown(f"""
                            <div class='glass-card'>
                                <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                    letter-spacing:1px; margin-bottom:8px;'>Suggested Action</div>
                                <div class='{action_cls}'>{action}</div>
                                <div style='margin-top:16px; display:flex; gap:20px;'>
                                    <div>
                                        <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                            letter-spacing:1px; margin-bottom:4px;'>Sentiment</div>
                                        <div style='color:#e2e8f0; font-weight:600;'>{sentiment}</div>
                                    </div>
                                    <div>
                                        <div style='color:#94a3b8; font-size:0.72rem; text-transform:uppercase;
                                            letter-spacing:1px; margin-bottom:4px;'>Horizon</div>
                                        <div style='color:#e2e8f0; font-weight:600;'>{horizon}</div>
                                    </div>
                                </div>
                                <div style='margin-top:16px; padding:14px; background:rgba(59,130,246,0.08);
                                    border:1px solid rgba(59,130,246,0.15); border-radius:10px;
                                    color:#94a3b8; font-size:0.85rem; line-height:1.6;'>
                                    💡 {summary}
                                </div>
                                <div style='margin-top:12px; padding:12px; background:rgba(239,68,68,0.08);
                                    border:1px solid rgba(239,68,68,0.15); border-radius:10px;
                                    color:#f59e0b; font-size:0.82rem;'>
                                    ⚠️ <strong>Risk:</strong> {risk}
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                        else:
                            st.info("No AI insight yet. Run the pipeline to generate.")

                    st.caption(f"Signal details: {sig.get('details','')}")


# ══════════════════════════════════════════════════════════
# PAGE 3: ACTIVITY LOG
# ══════════════════════════════════════════════════════════
elif "Activity Log" in page:
    st.markdown("""
    <div class='page-header'>📋 Agent Activity Log</div>
    <div class='page-subtitle'>Live view of the autonomous pipeline workflow</div>
    """, unsafe_allow_html=True)

    log_df = db.get_activity_log(limit=100)

    if log_df.empty:
        st.markdown("""
        <div class='glass-card' style='text-align:center; padding:60px 40px;'>
            <div style='font-size:3rem; margin-bottom:16px;'>📋</div>
            <div style='color:#e2e8f0; font-size:1.1rem; font-weight:600; margin-bottom:8px;'>
            No activity logged yet</div>
            <div style='color:#94a3b8; font-size:0.85rem;'>
            Run the pipeline from the sidebar to start.</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        # Build log entries HTML
        log_entries_html = ""
        for _, row in log_df.iterrows():
            level = row.get("level", "INFO")
            icon  = {"INFO":"ℹ️","WARN":"⚠️","ERROR":"❌"}.get(level, "ℹ️")
            color_map = {"INFO":"#94a3b8","WARN":"#f59e0b","ERROR":"#ef4444"}
            entry_color = color_map.get(level, "#94a3b8")
            log_entries_html += (
                f'<div class="log-entry" style="color:{entry_color}">'
                f'{icon} [{row.get("timestamp","")}] {row.get("message","")}'
                f'</div>\n'
            )

        st.markdown(f"""
        <div class="terminal-panel" id="terminal-log">
            <div class="terminal-header">
                <div class="terminal-dot"></div>
                <span class="terminal-title">LIVE</span>
                <span style="color:#64748b; font-size:0.72rem; margin-left:auto;">
                    {len(log_df)} entries</span>
            </div>
            {log_entries_html}
        </div>
        """, unsafe_allow_html=True)

        # Auto-scroll to bottom
        st.markdown("""
        <script>
            const terminal = document.getElementById('terminal-log');
            if (terminal) { terminal.scrollTop = terminal.scrollHeight; }
        </script>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:16px'></div>", unsafe_allow_html=True)

        if st.button("🗑️ Clear Log"):
            import sqlite3
            from utils.config import DB_PATH
            conn = sqlite3.connect(DB_PATH)
            conn.execute("DELETE FROM activity_log")
            conn.commit()
            conn.close()
            st.rerun()


# ══════════════════════════════════════════════════════════
# PAGE 4: PORTFOLIO SIMULATOR
# ══════════════════════════════════════════════════════════
elif "Portfolio Simulator" in page:
    st.markdown("""
    <div style='margin-bottom:24px'>
        <h1 style='font-family:Outfit,sans-serif;font-size:2rem;
        font-weight:800;color:#ffffff;margin-bottom:4px'>
        💼 Portfolio Simulator</h1>
        <p style='color:#94a3b8;font-family:JetBrains Mono,monospace;
        font-size:0.82rem'>Simulate returns if you followed every SignalSense signal</p>
    </div>
    """, unsafe_allow_html=True)

    # ── INPUT ──────────────────────────────────────────
    col1, col2, col3 = st.columns(3)
    with col1:
        portfolio_amount = st.number_input(
            "Starting Portfolio (₹)",
            min_value=10000,
            max_value=10000000,
            value=500000,
            step=10000,
            format="%d"
        )
    with col2:
        hold_days = st.selectbox(
            "Holding Period",
            options=[5, 10, 15, 30],
            index=0,
            format_func=lambda x: f"{x} days"
        )
    with col3:
        min_winrate = st.slider(
            "Min Win Rate Filter %",
            min_value=50,
            max_value=80,
            value=55
        )

    st.divider()

    # ── FETCH BACKTEST DATA ─────────────────────────────
    # Fetch backtests
    b_resp = orch.sb.table("backtest_results").select("*").gte("win_rate", min_winrate).order("win_rate", desc=True).execute()
    bt_df = pd.DataFrame(b_resp.data) if b_resp.data else pd.DataFrame()

    if not bt_df.empty:
        # Fetch matching insights
        symbols_list = bt_df["symbol"].unique().tolist()
        i_resp = orch.sb.table("insights").select("symbol, pattern, insight_json").in_("symbol", symbols_list).execute()
        i_df = pd.DataFrame(i_resp.data) if i_resp.data else pd.DataFrame()

        # Merge them (Left Join)
        if not i_df.empty:
            bt_df = pd.merge(bt_df, i_df, on=["symbol", "pattern"], how="left")
        else:
            bt_df["insight_json"] = None

    if bt_df.empty:
        st.warning("No backtest data found. Run the pipeline first.")
    else:
        # ── SIMULATION LOGIC ───────────────────────────
        import json

        # Equal allocation per signal
        num_signals     = len(bt_df)
        per_signal      = portfolio_amount / num_signals if num_signals > 0 else 0

        total_invested  = portfolio_amount
        total_returns   = 0
        wins            = 0
        losses          = 0
        best_trade      = {"symbol": "", "pattern": "", "return": 0}
        worst_trade     = {"symbol": "", "pattern": "", "return": 0}
        trade_log       = []

        for _, row in bt_df.iterrows():
            avg_ret    = row["avg_return"] / 100
            trade_pnl  = per_signal * avg_ret
            final_val  = per_signal + trade_pnl
            total_returns += trade_pnl

            if avg_ret > 0:
                wins += 1
            else:
                losses += 1

            if row["avg_return"] > best_trade["return"]:
                best_trade = {"symbol": row["symbol"], "pattern": row["pattern"], "return": row["avg_return"]}
            if row["avg_return"] < worst_trade["return"]:
                worst_trade = {"symbol": row["symbol"], "pattern": row["pattern"], "return": row["avg_return"]}

            # Get action from insight
            action = "Buy"
            if pd.notna(row.get("insight_json")):
                try:
                    action = json.loads(row["insight_json"]).get("suggested_action", "Buy")
                except:
                    action = "Buy"

            trade_log.append({
                "Symbol":      row["symbol"],
                "Pattern":     row["pattern"],
                "Win Rate":    f"{row['win_rate']:.1f}%",
                "Avg Return":  f"{row['avg_return']:.2f}%",
                "Invested":    f"₹{per_signal:,.0f}",
                "P&L":         f"₹{trade_pnl:+,.0f}",
                "Action":      action,
            })

        final_portfolio = portfolio_amount + total_returns

        # NIFTY50 benchmark — realistic 12% annual, scaled to hold period
        benchmark_annual  = 0.12
        benchmark_period  = benchmark_annual * (hold_days / 365) * num_signals
        benchmark_final   = portfolio_amount * (1 + benchmark_period)
        benchmark_return  = benchmark_final - portfolio_amount
        alpha             = total_returns - benchmark_return
        total_return_pct  = (total_returns / portfolio_amount) * 100
        benchmark_pct     = (benchmark_return / portfolio_amount) * 100
        alpha_pct         = total_return_pct - benchmark_pct

        # ── RESULT CARDS ───────────────────────────────
        st.markdown("""
        <div style='font-family:Outfit,sans-serif;font-size:0.75rem;
        color:#94a3b8;letter-spacing:2px;text-transform:uppercase;
        margin-bottom:16px'>Simulation Results</div>
        """, unsafe_allow_html=True)

        c1, c2, c3, c4 = st.columns(4)

        with c1:
            color = "#10b981" if final_portfolio > portfolio_amount else "#ef4444"
            st.markdown(f"""
            <div style='background:rgba(16,185,129,0.1);border:1px solid rgba(16,185,129,0.3);border-radius:16px;padding:20px;border-top:3px solid #10b981'>
                <div style='color:#94a3b8;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin-bottom:8px'>Final Portfolio</div>
                <div style='font-size:1.6rem;font-weight:800;color:{color};font-family:JetBrains Mono,monospace'>₹{final_portfolio:,.0f}</div>
                <div style='color:{color};font-size:0.82rem;margin-top:4px'>{total_return_pct:+.2f}% return</div>
            </div>
            """, unsafe_allow_html=True)

        with c2:
            st.markdown(f"""
            <div style='background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);border-radius:16px;padding:20px;border-top:3px solid #3b82f6'>
                <div style='color:#94a3b8;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin-bottom:8px'>NIFTY50 Benchmark</div>
                <div style='font-size:1.6rem;font-weight:800;color:#3b82f6;font-family:JetBrains Mono,monospace'>₹{benchmark_final:,.0f}</div>
                <div style='color:#3b82f6;font-size:0.82rem;margin-top:4px'>{benchmark_pct:+.2f}% return</div>
            </div>
            """, unsafe_allow_html=True)

        with c3:
            alpha_color = "#10b981" if alpha > 0 else "#ef4444"
            st.markdown(f"""
            <div style='background:rgba(168,85,247,0.1);border:1px solid rgba(168,85,247,0.3);border-radius:16px;padding:20px;border-top:3px solid #a855f7'>
                <div style='color:#94a3b8;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin-bottom:8px'>Alpha Generated</div>
                <div style='font-size:1.6rem;font-weight:800;color:{alpha_color};font-family:JetBrains Mono,monospace'>₹{alpha:+,.0f}</div>
                <div style='color:{alpha_color};font-size:0.82rem;margin-top:4px'>{alpha_pct:+.2f}% vs benchmark</div>
            </div>
            """, unsafe_allow_html=True)

        with c4:
            win_pct = (wins / (wins + losses) * 100) if (wins + losses) > 0 else 0
            st.markdown(f"""
            <div style='background:rgba(245,158,11,0.1);border:1px solid rgba(245,158,11,0.3);border-radius:16px;padding:20px;border-top:3px solid #f59e0b'>
                <div style='color:#94a3b8;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin-bottom:8px'>Win / Loss</div>
                <div style='font-size:1.6rem;font-weight:800;color:#f59e0b;font-family:JetBrains Mono,monospace'>{wins}W / {losses}L</div>
                <div style='color:#f59e0b;font-size:0.82rem;margin-top:4px'>{win_pct:.1f}% win rate</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ── COMPARISON BAR CHART ───────────────────────
        import plotly.graph_objects as go

        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=["Starting Capital", "SignalSense Portfolio", "NIFTY50 Benchmark"],
            y=[portfolio_amount, final_portfolio, benchmark_final],
            marker_color=["#475569", "#10b981", "#3b82f6"],
            text=[f"₹{portfolio_amount:,.0f}", f"₹{final_portfolio:,.0f}", f"₹{benchmark_final:,.0f}"],
            textposition="outside",
            textfont=dict(color="white", size=12, family="JetBrains Mono"),
        ))
        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0f172a",
            plot_bgcolor="#0f172a",
            title=dict(text="SignalSense vs NIFTY50 Benchmark", font=dict(size=16, color="#ffffff", family="Outfit, sans-serif")),
            yaxis=dict(tickprefix="₹", tickformat=",", gridcolor="rgba(255,255,255,0.05)"),
            showlegend=False,
            height=350,
            margin=dict(t=60, b=20, l=20, r=20),
        )
        st.plotly_chart(fig, width="stretch")

        st.divider()

        # ── BEST / WORST TRADES ────────────────────────
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"""
            <div style='background:rgba(16,185,129,0.08);border:1px solid rgba(16,185,129,0.25);border-radius:12px;padding:16px'>
                <div style='color:#10b981;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin-bottom:8px'>🏆 Best Signal</div>
                <div style='color:#ffffff;font-size:1.1rem;font-weight:700'>{best_trade["symbol"]}</div>
                <div style='color:#94a3b8;font-size:0.82rem'>{best_trade["pattern"]}</div>
                <div style='color:#10b981;font-size:1.2rem;font-weight:700;font-family:JetBrains Mono,monospace;margin-top:6px'>+{best_trade["return"]:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        with col_b:
            st.markdown(f"""
            <div style='background:rgba(239,68,68,0.08);border:1px solid rgba(239,68,68,0.25);border-radius:12px;padding:16px'>
                <div style='color:#ef4444;font-size:0.7rem;letter-spacing:1.5px;text-transform:uppercase;font-family:JetBrains Mono,monospace;margin-bottom:8px'>⚠️ Worst Signal</div>
                <div style='color:#ffffff;font-size:1.1rem;font-weight:700'>{worst_trade["symbol"]}</div>
                <div style='color:#94a3b8;font-size:0.82rem'>{worst_trade["pattern"]}</div>
                <div style='color:#ef4444;font-size:1.2rem;font-weight:700;font-family:JetBrains Mono,monospace;margin-top:6px'>{worst_trade["return"]:.2f}%</div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()

        # ── TRADE LOG TABLE ────────────────────────────
        st.markdown("""
        <div style='font-family:Outfit,sans-serif;font-size:0.75rem;color:#94a3b8;letter-spacing:2px;text-transform:uppercase;margin-bottom:12px'>📋 Full Trade Log</div>
        """, unsafe_allow_html=True)

        trade_df = pd.DataFrame(trade_log)
        st.dataframe(trade_df, width="stretch", hide_index=True)




# ── FOOTER ────────────────────────────────────────────────
st.divider()
st.markdown("""
<div class='footer-text'>
    SignalSense AI · Autonomous Stock Pattern Intelligence ·
    Not financial advice · Data from Google Finance via SerpAPI
</div>
""", unsafe_allow_html=True)
