"""
Module 6: Orchestrator Agent
Coordinates the full autonomous pipeline:
  Step 1 → Market Data Agent    (fetch OHLCV via SerpAPI)
  Step 2 → Pattern Agent        (detect signals)
  Step 3 → Backtest Agent       (compute win rates)
  Step 4 → Insight Agent        (generate LLM explanation)
  Step 5 → Alerts Agent         (push high-confidence alerts)
"""

from datetime import datetime
from agents.market_data_agent import MarketDataAgent
from agents.pattern_agent     import PatternAgent
from agents.backtest_agent    import BacktestAgent
from agents.insight_agent     import InsightAgent
from agents.alerts            import AlertsAgent
from data.database            import Database
from data.supabase_client     import get_client
from utils.config             import NIFTY50_SYMBOLS, MIN_CONFIDENCE_ALERT, MIN_WIN_RATE_ALERT


class Orchestrator:
    def __init__(self):
        self.market   = MarketDataAgent()
        self.patterns = PatternAgent()
        self.backtest = BacktestAgent()
        self.insight  = InsightAgent()
        self.alerts   = AlertsAgent()
        self.db       = Database()
        self.sb       = get_client()

    # ── LOGGING ──────────────────────────────────────────
    def _log(self, message: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] [{level}] {message}")
        try:
            self.sb.table("activity_log").insert({
                "timestamp": ts,
                "level":     level,
                "message":   message,
            }).execute()
        except Exception:
            pass  # Don't let logging failures break the pipeline

    # ── SINGLE SYMBOL PIPELINE ────────────────────────────
    def _process_symbol(self, symbol: str, force: bool = False) -> list[dict]:
        """
        Runs the full pipeline for one symbol.
        Returns list of alert-ready dicts.
        """
        alerts_ready = []

        # Step 1: Fetch data
        df = self.market.fetch(symbol, force=force)
        if df.empty or len(df) < 30:
            self._log(f"{symbol}: insufficient data ({len(df)} rows), skipping", "WARN")
            return []

        # Step 2: Detect patterns
        signals = self.patterns.run(symbol, df)
        if not signals:
            return []

        self._log(f"{symbol}: {len(signals)} pattern(s) detected")

        # Step 3 + 4: Backtest + Insight per signal
        bt_results = self.backtest.run(symbol, df)

        for sig in signals:
            pattern = sig["pattern"]
            bt      = bt_results.get(pattern, {})

            # Generate LLM insight
            ins = self.insight.run(sig, bt)

            # Build full alert record
            alert = {
                **sig,
                "win_rate":         bt.get("win_rate", 0),
                "avg_return":       bt.get("avg_return", 0),
                "risk_reward":      bt.get("risk_reward", 0),
                "total_occurrences":bt.get("total_occurrences", 0),
                "suggested_action": ins.get("suggested_action", "Watch"),
                "sentiment":        ins.get("sentiment", "Neutral"),
                "summary":          ins.get("summary", ""),
                "key_risk":         ins.get("key_risk", ""),
                "time_horizon":     ins.get("time_horizon", ""),
            }
            alerts_ready.append(alert)

        return alerts_ready

    # ── FULL PIPELINE ─────────────────────────────────────
    def run(self, symbols: list[str] = None, force: bool = False) -> list[dict]:
        """
        Run the complete autonomous pipeline for all symbols.
        Returns list of all alert records generated.
        """
        symbols    = symbols or NIFTY50_SYMBOLS
        all_alerts = []

        self._log(f"🚀 SignalSense pipeline started — {len(symbols)} symbols")

        for i, symbol in enumerate(symbols, 1):
            self._log(f"[{i}/{len(symbols)}] Processing {symbol}...")
            try:
                alerts = self._process_symbol(symbol, force=force)
                all_alerts.extend(alerts)
            except Exception as e:
                self._log(f"{symbol}: unexpected error — {e}", "ERROR")

        # Step 5: Push alerts for high-confidence signals
        self._log("📣 Pushing alerts...")
        pushed = 0
        for alert in all_alerts:
            conf     = alert.get("confidence", 0)
            win_rate = alert.get("win_rate", 0)
            if conf >= MIN_CONFIDENCE_ALERT and win_rate >= MIN_WIN_RATE_ALERT:
                self.alerts.send(alert)
                pushed += 1

        self._log(
            f"✅ Pipeline complete — {len(all_alerts)} signals, "
            f"{pushed} alerts pushed"
        )
        return all_alerts

    # ── QUICK SCAN (single stock) ──────────────────────────
    def scan_single(self, symbol: str) -> list[dict]:
        """Scan one stock on demand (used from dashboard)."""
        self._log(f"🔍 On-demand scan: {symbol}")
        return self._process_symbol(symbol, force=True)

    # ── STATUS ────────────────────────────────────────────
    def status(self) -> dict:
        return self.db.get_stats()
