"""
utils/config.py
Central configuration — API keys, paths, constants.
Load from environment variables or set directly here for development.
"""

import os
from dotenv import load_dotenv
load_dotenv()
# ── API KEYS ────────────────────────────────────────────
SERPAPI_KEY   = os.getenv("SERPAPI_KEY", "your_serpapi_key_here")
GROQ_API_KEY  = os.getenv("GROQ_API_KEY", "your_groq_api_key_here")

# ── SUPABASE ─────────────────────────────────────────────
SUPABASE_URL  = os.getenv("SUPABASE_URL", "")
SUPABASE_KEY  = os.getenv("SUPABASE_KEY", "")

# ── SERPAPI SETTINGS ─────────────────────────────────────
SERPAPI_BASE_URL  = "https://serpapi.com/search"
SERPAPI_ENGINE    = "google_finance"

# NSE suffix for Google Finance  (e.g. RELIANCE:NSE)
NSE_EXCHANGE      = "NSE"

# ── NIFTY 50 UNIVERSE ────────────────────────────────────
NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BHARTIARTL", "KOTAKBANK",
    "LT", "AXISBANK", "ASIANPAINT", "MARUTI", "BAJFINANCE",
    "HCLTECH", "SUNPHARMA", "TITAN", "ULTRACEMCO", "WIPRO",
    "NESTLEIND", "POWERGRID", "TECHM", "NTPC", "ONGC",
    "TATAMOTORS", "BAJAJFINSV", "JSWSTEEL", "COALINDIA", "ADANIENT",
    "ADANIPORTS", "TATASTEEL", "GRASIM", "DIVISLAB", "BPCL",
    "DRREDDY", "HINDALCO", "CIPLA", "EICHERMOT", "BRITANNIA",
    "SBILIFE", "HDFCLIFE", "APOLLOHOSP", "BAJAJ-AUTO", "TATACONSUM",
    "UPL", "HEROMOTOCO", "INDUSINDBK", "M&M", "SHREECEM"
]

# ── BACKTEST SETTINGS ─────────────────────────────────────
HOLD_DAYS        = 5          # Forward-return window (days)
MIN_OCCURRENCES  = 3          # Minimum pattern hits for valid backtest

# ── GROQ SETTINGS ────────────────────────────────────────
GROQ_MODEL       = "llama-3.3-70b-versatile"
GROQ_TEMPERATURE = 0.2
GROQ_MAX_TOKENS  = 500

# ── ALERT THRESHOLDS ─────────────────────────────────────
MIN_CONFIDENCE_ALERT = 65.0   # Only alert if confidence >= this value
MIN_WIN_RATE_ALERT   = 55.0   # Only alert if historical win rate >= this

# ── RATE LIMITS ───────────────────────────────────────────
# SerpAPI free tier: 100 searches/month  → use sparingly
SERPAPI_DELAY_SEC = 2         # Seconds between SerpAPI calls
