"""
Module 5: Database Layer
Central SQLite interface — read helpers used by orchestrator & dashboard.
All write operations are handled by the individual agents.
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from utils.config import DB_PATH


class Database:
    def __init__(self):
        self.path = DB_PATH

    def _conn(self):
        return sqlite3.connect(self.path)

    # ── OHLCV ─────────────────────────────────────────────
    def get_ohlcv(self, symbol: str, days: int = 730) -> pd.DataFrame:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        conn   = self._conn()
        df     = pd.read_sql(
            "SELECT * FROM ohlcv WHERE symbol=? AND date>=? ORDER BY date ASC",
            conn, params=(symbol, cutoff)
        )
        conn.close()
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
        return df

    def get_all_symbols(self) -> list[str]:
        conn   = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv")
        syms   = [r[0] for r in cursor.fetchall()]
        conn.close()
        return syms

    def get_latest_price(self, symbol: str) -> float | None:
        conn   = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT close FROM ohlcv WHERE symbol=? ORDER BY date DESC LIMIT 1",
            (symbol,)
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None

    def get_summary(self, symbol: str) -> dict:
        conn   = self._conn()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stock_summary WHERE symbol=?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {}
        cols = ["symbol","price","change","change_pct","market_cap",
                "pe_ratio","exchange","currency","last_updated"]
        return dict(zip(cols, row))

    # ── SIGNALS ───────────────────────────────────────────
    def get_signals(self, symbol: str = None, limit: int = 100) -> pd.DataFrame:
        conn = self._conn()
        if symbol:
            df = pd.read_sql(
                "SELECT * FROM signals WHERE symbol=? ORDER BY created_at DESC LIMIT ?",
                conn, params=(symbol, limit)
            )
        else:
            df = pd.read_sql(
                "SELECT * FROM signals ORDER BY created_at DESC LIMIT ?",
                conn, params=(limit,)
            )
        conn.close()
        return df

    def get_today_signals(self) -> pd.DataFrame:
        today = datetime.now().strftime("%Y-%m-%d")
        conn  = self._conn()
        df    = pd.read_sql(
            "SELECT * FROM signals WHERE date=? ORDER BY confidence DESC",
            conn, params=(today,)
        )
        conn.close()
        return df

    # ── BACKTEST ──────────────────────────────────────────
    def get_backtest(self, symbol: str, pattern: str) -> dict:
        conn   = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM backtest_results WHERE symbol=? AND pattern=?",
            (symbol, pattern)
        )
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {}
        cols = ["id","symbol","pattern","win_rate","avg_return","max_drawdown",
                "total_occurrences","profitable_trades","avg_win","avg_loss",
                "risk_reward","created_at"]
        return dict(zip(cols, row))

    def get_all_backtests(self) -> pd.DataFrame:
        conn = self._conn()
        df   = pd.read_sql("SELECT * FROM backtest_results ORDER BY win_rate DESC", conn)
        conn.close()
        return df

    # ── INSIGHTS ──────────────────────────────────────────
    def get_insight(self, symbol: str, pattern: str, date: str) -> dict:
        conn   = self._conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT insight_json FROM insights WHERE symbol=? AND pattern=? AND date=?",
            (symbol, pattern, date)
        )
        row = cursor.fetchone()
        conn.close()
        return json.loads(row[0]) if row else {}

    # ── ACTIVITY LOG ─────────────────────────────────────
    def get_activity_log(self, limit: int = 50) -> pd.DataFrame:
        conn = self._conn()
        try:
            df = pd.read_sql(
                "SELECT * FROM activity_log ORDER BY id DESC LIMIT ?",
                conn, params=(limit,)
            )
        except Exception:
            df = pd.DataFrame(columns=["id","timestamp","level","message"])
        conn.close()
        return df.iloc[::-1].reset_index(drop=True)  # chronological order

    # ── DASHBOARD AGGREGATE ───────────────────────────────
    def get_market_radar(self) -> pd.DataFrame:
        """
        Joins signals + backtest + insights into a single radar table.
        Used by the dashboard Market Radar view.
        """
        conn = self._conn()
        sig  = pd.read_sql(
            "SELECT symbol, date, pattern, confidence, details "
            "FROM signals ORDER BY created_at DESC LIMIT 300",
            conn
        )
        bt   = pd.read_sql(
            "SELECT symbol, pattern, win_rate, avg_return, risk_reward "
            "FROM backtest_results",
            conn
        )
        ins  = pd.read_sql(
            "SELECT symbol, pattern, date, insight_json FROM insights",
            conn
        )
        conn.close()

        if sig.empty:
            return pd.DataFrame()

        merged = sig.merge(bt,  on=["symbol","pattern"], how="left")
        merged = merged.merge(ins, on=["symbol","pattern","date"], how="left")

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
        conn   = self._conn()
        cursor = conn.cursor()

        def q(sql, params=()):
            cursor.execute(sql, params)
            row = cursor.fetchone()
            return row[0] if row and row[0] is not None else 0

        stats = {
            "stocks_tracked": q("SELECT COUNT(DISTINCT symbol) FROM ohlcv"),
            "total_signals":  q("SELECT COUNT(*) FROM signals"),
            "today_signals":  q("SELECT COUNT(*) FROM signals WHERE date=?",
                                (datetime.now().strftime("%Y-%m-%d"),)),
            "avg_win_rate":   round(q("SELECT AVG(win_rate) FROM backtest_results"), 1),
        }
        conn.close()
        return stats
