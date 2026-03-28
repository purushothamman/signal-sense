"""
Module 5: Database Layer
Central Supabase interface — read helpers used by orchestrator & dashboard.
All write operations are handled by the individual agents.
"""

import pandas as pd
import json
from datetime import datetime, timedelta
from data.supabase_client import get_client


class Database:
    def __init__(self):
        self.client = get_client()

    # ── OHLCV ─────────────────────────────────────────────
    def get_ohlcv(self, symbol: str, days: int = 730) -> pd.DataFrame:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        resp = (
            self.client.table("ohlcv")
            .select("*")
            .eq("symbol", symbol)
            .gte("date", cutoff)
            .order("date")
            .execute()
        )
        df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
        return df

    def get_all_symbols(self) -> list[str]:
        resp = self.client.table("last_updated").select("symbol").execute()
        if not resp.data:
            return []
        return sorted(list({row["symbol"] for row in resp.data}))

    def get_latest_price(self, symbol: str) -> float | None:
        resp = (
            self.client.table("ohlcv")
            .select("close")
            .eq("symbol", symbol)
            .order("date", desc=True)
            .limit(1)
            .execute()
        )
        if resp.data:
            return resp.data[0]["close"]
        return None

    def get_summary(self, symbol: str) -> dict:
        resp = (
            self.client.table("stock_summary")
            .select("*")
            .eq("symbol", symbol)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return {}

    # ── SIGNALS ───────────────────────────────────────────
    def get_signals(self, symbol: str = None, limit: int = 100) -> pd.DataFrame:
        query = self.client.table("signals").select("*")
        if symbol:
            query = query.eq("symbol", symbol)
        resp = query.order("created_at", desc=True).limit(limit).execute()
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

    def get_today_signals(self) -> pd.DataFrame:
        today = datetime.now().strftime("%Y-%m-%d")
        resp = (
            self.client.table("signals")
            .select("*")
            .eq("date", today)
            .order("confidence", desc=True)
            .execute()
        )
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

    # ── BACKTEST ──────────────────────────────────────────
    def get_backtest(self, symbol: str, pattern: str) -> dict:
        resp = (
            self.client.table("backtest_results")
            .select("*")
            .eq("symbol", symbol)
            .eq("pattern", pattern)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return {}

    def get_all_backtests(self) -> pd.DataFrame:
        resp = (
            self.client.table("backtest_results")
            .select("*")
            .order("win_rate", desc=True)
            .execute()
        )
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()

    # ── INSIGHTS ──────────────────────────────────────────
    def get_insight(self, symbol: str, pattern: str, date: str) -> dict:
        resp = (
            self.client.table("insights")
            .select("insight_json")
            .eq("symbol", symbol)
            .eq("pattern", pattern)
            .eq("date", date)
            .execute()
        )
        if resp.data:
            return json.loads(resp.data[0]["insight_json"])
        return {}

    # ── ACTIVITY LOG ─────────────────────────────────────
    def get_activity_log(self, limit: int = 50) -> pd.DataFrame:
        try:
            resp = (
                self.client.table("activity_log")
                .select("*")
                .order("id", desc=True)
                .limit(limit)
                .execute()
            )
            df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame(
                columns=["id", "timestamp", "level", "message"]
            )
        except Exception:
            df = pd.DataFrame(columns=["id", "timestamp", "level", "message"])
        return df.iloc[::-1].reset_index(drop=True)  # chronological order

    # ── DASHBOARD AGGREGATE ───────────────────────────────
    def get_market_radar(self) -> pd.DataFrame:
        """
        Joins signals + backtest + insights into a single radar table.
        Used by the dashboard Market Radar view.
        """
        sig_resp = (
            self.client.table("signals")
            .select("symbol, date, pattern, confidence, details")
            .order("created_at", desc=True)
            .limit(300)
            .execute()
        )
        sig = pd.DataFrame(sig_resp.data) if sig_resp.data else pd.DataFrame()

        bt_resp = (
            self.client.table("backtest_results")
            .select("symbol, pattern, win_rate, avg_return, risk_reward")
            .execute()
        )
        bt = pd.DataFrame(bt_resp.data) if bt_resp.data else pd.DataFrame()

        ins_resp = (
            self.client.table("insights")
            .select("symbol, pattern, date, insight_json")
            .execute()
        )
        ins = pd.DataFrame(ins_resp.data) if ins_resp.data else pd.DataFrame()

        if sig.empty:
            return pd.DataFrame()

        merged = sig.merge(bt, on=["symbol", "pattern"], how="left")
        merged = merged.merge(ins, on=["symbol", "pattern", "date"], how="left")

        def _extract(j, key, default="—"):
            try:
                return json.loads(j).get(key, default) if pd.notna(j) else default
            except Exception:
                return default

        if "insight_json" in merged.columns:
            merged["suggested_action"] = merged["insight_json"].apply(
                lambda j: _extract(j, "suggested_action", "Watch"))
            merged["sentiment"] = merged["insight_json"].apply(
                lambda j: _extract(j, "sentiment", "Neutral"))

        return merged.drop(columns=["insight_json"], errors="ignore")

    # ── STATS ─────────────────────────────────────────────
    def get_stats(self) -> dict:
        try:
            # stocks tracked
            ohlcv_resp = self.client.table("last_updated").select("symbol", count="exact").execute()
            stocks_tracked = ohlcv_resp.count if ohlcv_resp.count is not None else 0

            # total signals
            sig_resp = self.client.table("signals").select("id", count="exact").execute()
            total_signals = sig_resp.count if sig_resp.count is not None else 0

            # today signals
            today = datetime.now().strftime("%Y-%m-%d")
            today_resp = (
                self.client.table("signals")
                .select("id", count="exact")
                .eq("date", today)
                .execute()
            )
            today_signals = today_resp.count if today_resp.count is not None else 0

            # avg win rate
            bt_resp = self.client.table("backtest_results").select("win_rate").execute()
            if bt_resp.data:
                win_rates = [r["win_rate"] for r in bt_resp.data if r["win_rate"] is not None]
                avg_win_rate = round(sum(win_rates) / len(win_rates), 1) if win_rates else 0
            else:
                avg_win_rate = 0

            return {
                "stocks_tracked": stocks_tracked,
                "total_signals": total_signals,
                "today_signals": today_signals,
                "avg_win_rate": avg_win_rate,
            }
        except Exception:
            return {
                "stocks_tracked": 0,
                "total_signals": 0,
                "today_signals": 0,
                "avg_win_rate": 0,
            }
