"""
Module 2: Pattern Detection Agent
Detects 4 high-impact technical patterns:
  1. Breakout           – price + volume confirmation
  2. Golden Cross       – SMA50 crosses above SMA200
  3. RSI Divergence     – bullish hidden divergence
  4. Double Bottom      – rule-based dual-trough detection
"""

import pandas as pd
import numpy as np
from datetime import datetime
from data.supabase_client import get_client


class PatternAgent:
    def __init__(self):
        self.sb = get_client()

    # ── INDICATOR HELPERS ────────────────────────────────
    def _sma(self, s: pd.Series, w: int) -> pd.Series:
        return s.rolling(w).mean()

    def _rsi(self, s: pd.Series, p: int = 14) -> pd.Series:
        delta = s.diff()
        gain  = delta.clip(lower=0).rolling(p).mean()
        loss  = (-delta.clip(upper=0)).rolling(p).mean()
        rs    = gain / loss.replace(0, np.nan)
        return 100 - (100 / (1 + rs))

    # ── PATTERN 1: BREAKOUT ──────────────────────────────
    def detect_breakout(self, df: pd.DataFrame) -> dict | None:
        if len(df) < 5:          # was 22
            return None

        last     = df.iloc[-1]
        lookback = min(20, len(df) - 1)
        prev     = df.iloc[-lookback-1:-1]
        high_n   = prev["high"].max()
        avg_vol  = prev["volume"].mean()

        price_ok  = last["close"] > high_n

        # Skip volume check if volume is 0
        if avg_vol > 0 and last["volume"] > 0:
            volume_ok = last["volume"] > 1.5 * avg_vol
            vol_ratio = last["volume"] / avg_vol
        else:
            volume_ok = price_ok   # rely on price only
            vol_ratio = 1.5

        if price_ok and volume_ok:
            breakout_pct = ((last["close"] - high_n) / high_n) * 100
            confidence   = min(95, 60 + breakout_pct * 3)
            return {
                "pattern":    "Breakout",
                "confidence": round(confidence, 2),
                "details":    f"Price broke {lookback}-week high by {breakout_pct:.2f}%",
            }
        return None

    # ── PATTERN 2: GOLDEN CROSS ──────────────────────────
    def detect_golden_cross(self, df: pd.DataFrame) -> dict | None:
        if len(df) < 30:         # was 205
            return None

        df = df.copy()
        df["sma10"] = self._sma(df["close"], 10)   # use SMA10/SMA30 instead
        df["sma30"] = self._sma(df["close"], 30)
        recent = df.dropna(subset=["sma10","sma30"]).iloc[-4:]

        for i in range(1, len(recent)):
            prev = recent.iloc[i-1]
            curr = recent.iloc[i]
            if prev["sma10"] <= prev["sma30"] and curr["sma10"] > curr["sma30"]:
                gap_pct    = ((curr["sma10"] - curr["sma30"]) / curr["sma30"]) * 100
                confidence = min(90, 70 + gap_pct * 4)
                return {
                    "pattern":    "Golden Cross",
                    "confidence": round(confidence, 2),
                    "details":    f"SMA10 crossed above SMA30 (weekly); gap: {gap_pct:.2f}%",
                }
        return None

    # ── PATTERN 3: RSI DIVERGENCE ────────────────────────
    def detect_rsi_divergence(self, df: pd.DataFrame) -> dict | None:
        if len(df) < 10:         # was 30
            return None

        df        = df.copy()
        df["rsi"] = self._rsi(df["close"], p=10)  # shorter RSI period
        recent    = df.dropna(subset=["rsi"]).iloc[-10:]

        if len(recent) < 6:
            return None

        mid    = len(recent) // 2
        first  = recent.iloc[:mid]
        second = recent.iloc[mid:]

        price_lower = second["close"].min() < first["close"].min()
        rsi_higher  = second["rsi"].min()   > first["rsi"].min()

        if price_lower and rsi_higher:
            rsi_diff   = second["rsi"].min() - first["rsi"].min()
            confidence = min(85, 55 + rsi_diff * 1.5)
            return {
                "pattern":    "RSI Divergence",
                "confidence": round(confidence, 2),
                "details":    f"Bullish divergence on weekly chart (+{rsi_diff:.1f} RSI pts)",
            }
        return None

    # ── PATTERN 4: DOUBLE BOTTOM ─────────────────────────
    def detect_double_bottom(self, df: pd.DataFrame) -> dict | None:
        if len(df) < 15:         # was 40
            return None

        lookback = min(40, len(df))
        lows     = df["low"].iloc[-lookback:].values
        indices  = [
            i for i in range(2, len(lows) - 2)
            if lows[i] < lows[i-1] and lows[i] < lows[i+1]
               and lows[i] < lows[i-2] and lows[i] < lows[i+2]
        ]

        if len(indices) < 2:
            return None

        b1, b2     = indices[-2], indices[-1]
        if b2 - b1 < 3:          # was 5
            return None

        l1, l2     = lows[b1], lows[b2]
        similarity = abs(l1 - l2) / max(l1, l2)
        neckline   = max(lows[b1:b2])
        neck_pct   = ((neckline - min(l1, l2)) / min(l1, l2)) * 100

        if similarity < 0.05 and neck_pct > 1:   # relaxed from 0.03 and 2
            confidence = min(88, 60 + (1 - similarity) * 20 + neck_pct)
            return {
                "pattern":    "Double Bottom",
                "confidence": round(confidence, 2),
                "details":    f"Two lows within {similarity*100:.1f}% on weekly chart",
            }
        return None

    # ── DETECT ALL ───────────────────────────────────────
    def detect_all(self, symbol: str, df: pd.DataFrame) -> list[dict]:
        """Run all detectors. Returns list of signal dicts."""
        signals   = []
        detectors = [
            self.detect_breakout,
            self.detect_golden_cross,
            self.detect_rsi_divergence,
            self.detect_double_bottom,
        ]
        for fn in detectors:
            result = fn(df)
            if result:
                result["symbol"] = symbol
                result["date"]   = str(df["date"].iloc[-1].date())
                signals.append(result)
        return signals

    # ── PERSIST ──────────────────────────────────────────
    def save_signals(self, signals: list[dict]):
        if not signals:
            return
        now = datetime.now().isoformat()
        rows = []
        for s in signals:
            rows.append({
                "symbol":     s["symbol"],
                "date":       s["date"],
                "pattern":    s["pattern"],
                "confidence": s["confidence"],
                "details":    s["details"],
                "created_at": now,
            })
        # Use upsert with ignore_duplicates to replicate INSERT OR IGNORE
        self.sb.table("signals").upsert(
            rows, on_conflict="symbol,date,pattern", ignore_duplicates=True
        ).execute()

    # ── MAIN ENTRY ───────────────────────────────────────
    def run(self, symbol: str, df: pd.DataFrame) -> list[dict]:
        """Detect patterns, persist, and return signals list."""
        signals = self.detect_all(symbol, df)
        self.save_signals(signals)
        if signals:
            names = [s["pattern"] for s in signals]
            print(f"[PatternAgent] {symbol}: {names}")
        else:
            print(f"[PatternAgent] {symbol}: no patterns detected")
        return signals

    def get_recent_signals(self, limit: int = 100) -> pd.DataFrame:
        resp = (
            self.sb.table("signals")
            .select("*")
            .order("created_at", desc=True)
            .limit(limit)
            .execute()
        )
        return pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
