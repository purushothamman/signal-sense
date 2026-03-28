"""
Module 7: Alerts Agent
Pushes actionable signal alerts to:
  - Console (always)
  - Telegram Bot (optional — set TELEGRAM_TOKEN + TELEGRAM_CHAT_ID in config)
"""

import os
import requests
from datetime import datetime
from data.supabase_client import get_client

TELEGRAM_TOKEN   = os.getenv("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class AlertsAgent:
    def __init__(self):
        self.sb               = get_client()
        self.telegram_enabled = bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID)

    # ── FORMAT ───────────────────────────────────────────
    def _format_message(self, alert: dict) -> str:
        action_emoji = {
            "Buy":   "🟢",
            "Watch": "🟡",
            "Avoid": "🔴",
        }.get(alert.get("suggested_action", "Watch"), "⚪")

        sentiment_emoji = {
            "Bullish":           "📈",
            "Cautiously Bullish":"📊",
            "Neutral":           "➡️",
            "Bearish":           "📉",
        }.get(alert.get("sentiment", "Neutral"), "➡️")

        return (
            f"🔔 *SignalSense Alert*\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"📌 *{alert.get('symbol')}* — {alert.get('pattern')}\n"
            f"📅 Date: {alert.get('date')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"{action_emoji} *Action : {alert.get('suggested_action')}*\n"
            f"{sentiment_emoji} Sentiment : {alert.get('sentiment')}\n"
            f"🎯 Confidence : {alert.get('confidence')}%\n"
            f"📊 Win Rate   : {alert.get('win_rate')}%\n"
            f"💹 Avg Return : {alert.get('avg_return', 0):.2f}%\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"💡 {alert.get('summary', '')}\n"
            f"⚠️  Risk: {alert.get('key_risk', '')}\n"
            f"⏱️  Horizon: {alert.get('time_horizon', '')}\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"_SignalSense AI — Not financial advice_"
        )

    # ── CONSOLE ALERT ─────────────────────────────────────
    def _console_alert(self, alert: dict):
        print("\n" + "="*55)
        print(f"  🔔 SIGNAL ALERT: {alert.get('symbol')} | {alert.get('pattern')}")
        print(f"  Action    : {alert.get('suggested_action')}")
        print(f"  Confidence: {alert.get('confidence')}%")
        print(f"  Win Rate  : {alert.get('win_rate')}%")
        print(f"  {alert.get('summary', '')}")
        print("="*55 + "\n")

    # ── TELEGRAM ALERT ────────────────────────────────────
    def _telegram_alert(self, alert: dict) -> bool:
        if not self.telegram_enabled:
            return False
        url     = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id":    TELEGRAM_CHAT_ID,
            "text":       self._format_message(alert),
            "parse_mode": "Markdown",
        }
        try:
            resp = requests.post(url, json=payload, timeout=10)
            return resp.status_code == 200
        except Exception as e:
            print(f"[AlertsAgent] Telegram error: {e}")
            return False

    # ── SAVE TO SUPABASE ─────────────────────────────────
    def _save(self, alert: dict):
        self.sb.table("alerts").insert({
            "symbol":           alert.get("symbol"),
            "pattern":          alert.get("pattern"),
            "date":             alert.get("date"),
            "confidence":       alert.get("confidence"),
            "win_rate":         alert.get("win_rate"),
            "suggested_action": alert.get("suggested_action"),
            "sentiment":        alert.get("sentiment"),
            "summary":          alert.get("summary"),
            "sent_at":          datetime.now().isoformat(),
        }).execute()

    # ── PUBLIC: SEND ─────────────────────────────────────
    def send(self, alert: dict):
        """Send alert via all configured channels."""
        self._console_alert(alert)
        self._telegram_alert(alert)
        self._save(alert)

    def get_recent_alerts(self, limit: int = 20):
        import pandas as pd
        resp = (
            self.sb.table("alerts")
            .select("*")
            .order("sent_at", desc=True)
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
