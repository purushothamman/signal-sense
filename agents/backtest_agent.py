"""
Module 3: Backtesting Agent
Replays all historical pattern occurrences on stored OHLCV data
and computes win rate, avg return, drawdown, and risk/reward.

forward_return = (close[i + HOLD_DAYS] - close[i]) / close[i] × 100
success        = forward_return > 0
"""

import pandas as pd
import numpy as np
from datetime import datetime
from utils.config import HOLD_DAYS, MIN_OCCURRENCES
from data.supabase_client import get_client


class BacktestAgent:
    def __init__(self):
        self.hold_days = HOLD_DAYS
        self.sb        = get_client()

    # ── HISTORICAL PATTERN SCANNERS ──────────────────────
    # Lightweight re-implementations (no DB writes) for fast backtesting.

    def _scan_breakout(self, df: pd.DataFrame) -> list[int]:
        hits = []
        for i in range(20, len(df) - self.hold_days):
            prev   = df.iloc[i-20:i]
            curr   = df.iloc[i]
            avg_v  = prev["volume"].mean()
            if (curr["close"] > prev["high"].max()
                    and avg_v > 0
                    and curr["volume"] > 1.5 * avg_v):
                hits.append(i)
        return hits

    def _scan_golden_cross(self, df: pd.DataFrame) -> list[int]:
        if len(df) < 205:
            return []
        df = df.copy()
        df["sma50"]  = df["close"].rolling(50).mean()
        df["sma200"] = df["close"].rolling(200).mean()
        hits = []
        for i in range(201, len(df) - self.hold_days):
            p, c = df.iloc[i-1], df.iloc[i]
            if pd.notna(p["sma50"]) and pd.notna(p["sma200"]):
                if p["sma50"] <= p["sma200"] and c["sma50"] > c["sma200"]:
                    hits.append(i)
        return hits

    def _scan_rsi_divergence(self, df: pd.DataFrame) -> list[int]:
        df = df.copy()
        delta  = df["close"].diff()
        gain   = delta.clip(lower=0).rolling(14).mean()
        loss   = (-delta.clip(upper=0)).rolling(14).mean()
        df["rsi"] = 100 - (100 / (1 + gain / loss.replace(0, np.nan)))
        hits = []
        for i in range(30, len(df) - self.hold_days):
            w   = df.iloc[i-15:i].dropna(subset=["rsi"])
            if len(w) < 6:
                continue
            mid = len(w) // 2
            f, s = w.iloc[:mid], w.iloc[mid:]
            if (s["close"].min() < f["close"].min()
                    and s["rsi"].min() > f["rsi"].min()):
                hits.append(i)
        return hits

    def _scan_double_bottom(self, df: pd.DataFrame) -> list[int]:
        hits = []
        for i in range(40, len(df) - self.hold_days):
            lows = df["low"].iloc[i-40:i].values
            troughs = [j for j in range(2, len(lows)-2)
                       if lows[j] < lows[j-1] and lows[j] < lows[j+1]
                       and lows[j] < lows[j-2] and lows[j] < lows[j+2]]
            if len(troughs) < 2:
                continue
            b1, b2 = troughs[-2], troughs[-1]
            if b2 - b1 < 5:
                continue
            sim = abs(lows[b1] - lows[b2]) / max(lows[b1], lows[b2])
            if sim < 0.03:
                hits.append(i)
        return hits

    # ── METRICS CALCULATOR ───────────────────────────────
    def _calc_metrics(self, df: pd.DataFrame, indices: list[int]) -> dict:
        returns = []
        for idx in indices:
            if idx + self.hold_days >= len(df):
                continue
            entry  = df["close"].iloc[idx]
            exit_p = df["close"].iloc[idx + self.hold_days]
            if entry <= 0:
                continue
            returns.append(((exit_p - entry) / entry) * 100)

        if len(returns) < MIN_OCCURRENCES:
            return {}

        arr  = np.array(returns)
        wins = arr[arr > 0]
        loss = arr[arr <= 0]

        win_rate    = len(wins) / len(arr) * 100
        avg_return  = float(np.mean(arr))
        avg_win     = float(np.mean(wins))  if len(wins) else 0.0
        avg_loss    = float(np.mean(loss))  if len(loss) else 0.0
        risk_reward = abs(avg_win / avg_loss) if avg_loss != 0 else 0.0

        # Max drawdown over the sequence of trades
        cumret   = np.cumprod(1 + arr / 100)
        run_max  = np.maximum.accumulate(cumret)
        dd       = (cumret - run_max) / run_max * 100
        max_dd   = float(np.min(dd))

        return {
            "win_rate":          round(win_rate, 2),
            "avg_return":        round(avg_return, 2),
            "avg_win":           round(avg_win, 2),
            "avg_loss":          round(avg_loss, 2),
            "max_drawdown":      round(max_dd, 2),
            "total_occurrences": len(returns),
            "profitable_trades": int(len(wins)),
            "risk_reward":       round(risk_reward, 2),
        }

    # ── PUBLIC RUN ───────────────────────────────────────
    def run(self, symbol: str, df: pd.DataFrame) -> dict:
        """
        Run backtests for all 4 patterns on a symbol's history.
        Returns {pattern_name: metrics_dict}.
        """
        scanners = {
            "Breakout":      self._scan_breakout,
            "Golden Cross":  self._scan_golden_cross,
            "RSI Divergence":self._scan_rsi_divergence,
            "Double Bottom": self._scan_double_bottom,
        }

        results = {}
        now     = datetime.now().isoformat()

        for name, scanner in scanners.items():
            indices = scanner(df)
            if not indices:
                continue
            metrics = self._calc_metrics(df, indices)
            if not metrics:
                continue

            results[name] = {**metrics, "symbol": symbol, "pattern": name}

            self.sb.table("backtest_results").upsert({
                "symbol":            symbol,
                "pattern":           name,
                "win_rate":          metrics["win_rate"],
                "avg_return":        metrics["avg_return"],
                "max_drawdown":      metrics["max_drawdown"],
                "total_occurrences": metrics["total_occurrences"],
                "profitable_trades": metrics["profitable_trades"],
                "avg_win":           metrics["avg_win"],
                "avg_loss":          metrics["avg_loss"],
                "risk_reward":       metrics["risk_reward"],
                "created_at":        now,
            }, on_conflict="symbol,pattern").execute()

            print(f"[BacktestAgent] {symbol} | {name} | "
                  f"WinRate={metrics['win_rate']}% | "
                  f"AvgReturn={metrics['avg_return']}% | "
                  f"N={metrics['total_occurrences']}")

        return results

    def get(self, symbol: str, pattern: str) -> dict:
        """Fetch a single backtest result."""
        resp = (
            self.sb.table("backtest_results")
            .select("*")
            .eq("symbol", symbol)
            .eq("pattern", pattern)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return {}

    def get_all(self) -> pd.DataFrame:
        resp = (
            self.sb.table("backtest_results")
            .select("*")
            .order("win_rate", desc=True)
            .execute()
        )
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
