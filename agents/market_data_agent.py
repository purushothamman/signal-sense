"""
Module 1: Market Data Agent
Fetches stock data from SerpAPI Google Finance.

SerpAPI Google Finance provides:
  - summary  : current price, change, market cap, P/E etc.
  - graph     : historical price points (use window=MAX for 2yr history)
  - news      : latest headlines for the stock

NSE symbol format for Google Finance: RELIANCE:NSE
"""

import requests
import pandas as pd
import time
from datetime import datetime, timedelta
from utils.config import (
    SERPAPI_KEY, SERPAPI_BASE_URL, NSE_EXCHANGE,
    NIFTY50_SYMBOLS, SERPAPI_DELAY_SEC
)
from data.supabase_client import get_client


class MarketDataAgent:
    def __init__(self):
        self.api_key = SERPAPI_KEY
        self.sb      = get_client()

    # ── SERPAPI CALL ─────────────────────────────────────
    def _fetch_google_finance(self, symbol: str, window: str = "MAX") -> dict:
        """
        Call SerpAPI Google Finance endpoint.
        Returns raw JSON response dict.

        symbol  : e.g. 'RELIANCE:NSE'
        window  : '1D','5D','1M','6M','YTD','1Y','5Y','MAX'
        """
        params = {
            "engine":  "google_finance",
            "q":       symbol,
            "window":  window,
            "api_key": self.api_key,
        }
        try:
            resp = requests.get(SERPAPI_BASE_URL, params=params, timeout=15)
            resp.raise_for_status()
            return resp.json()
        except requests.RequestException as e:
            print(f"[MarketDataAgent] API error for {symbol}: {e}")
            return {}

    # ── PARSE GRAPH → OHLCV ─────────────────────────────
    def _parse_graph_to_ohlcv(self, symbol: str, data: dict) -> pd.DataFrame:
        """
        Google Finance 'graph' key returns a list of price points:
        [{ "date": "Nov 12, 2022", "price": 2345.50, "volume": 1234567 }, ...]

        We treat each day's price as both open & close (only close & volume
        are available; high/low are estimated ±0.5% as placeholders).
        For pattern detection we use close & volume which ARE accurate.
        """
        graph = data.get("graph", [])
        if not graph:
            return pd.DataFrame()

        rows = []
        for point in graph:
            raw_date = point.get("date") or point.get("time", "")
            price    = point.get("price")
            volume   = point.get("volume", 0)

            if not raw_date or price is None:
                continue

            try:
                parsed_date = pd.to_datetime(raw_date)
            except Exception:
                continue

            # Estimate high/low as ±0.5% of close (Google Finance graph only gives price)
            rows.append({
                "symbol": symbol.split(":")[0],
                "date":   parsed_date,
                "open":   round(price * 0.9975, 2),
                "high":   round(price * 1.005,  2),
                "low":    round(price * 0.995,  2),
                "close":  round(price, 2),
                "volume": volume if volume else 0,
            })

        df = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
        df = df.drop_duplicates(subset=["date"])
        return df

    # ── PARSE SUMMARY ────────────────────────────────────
    def _parse_summary(self, symbol: str, data: dict) -> dict:
        """Extract quote summary from SerpAPI response."""
        summary = data.get("summary", {})
        markets = data.get("markets", {})

        price      = summary.get("price") or summary.get("previous_close")
        change     = summary.get("price_change", {})

        def _to_float(val):
            if val is None:
                return 0.0
            if isinstance(val, (int, float)):
                return float(val)
            import re
            cleaned = re.sub(r'[^\d.-]', '', str(val))
            try:
                return float(cleaned)
            except ValueError:
                return 0.0

        return {
            "symbol":       symbol.split(":")[0],
            "price":        _to_float(price),
            "change":       _to_float(change.get("amount", 0)),
            "change_pct":   _to_float(change.get("percentage", 0)),
            "market_cap":   summary.get("market_cap", ""),
            "pe_ratio":     _to_float(summary.get("pe_ratio")) if summary.get("pe_ratio") else None,
            "exchange":     summary.get("exchange", NSE_EXCHANGE),
            "currency":     summary.get("currency", "INR"),
            "last_updated": datetime.now().isoformat(),
        }

    # ── SAVE TO SUPABASE ────────────────────────────────
    def _save_ohlcv(self, df: pd.DataFrame):
        if df.empty:
            return
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).astype(str)
        rows = df.to_dict(orient="records")

        # Batch upsert in chunks of 500 (Supabase limit)
        chunk_size = 500
        for i in range(0, len(rows), chunk_size):
            chunk = rows[i:i + chunk_size]
            self.sb.table("ohlcv").upsert(
                chunk, on_conflict="symbol,date"
            ).execute()

    def _save_summary(self, s: dict):
        if not s or not s.get("price"):
            return
        self.sb.table("stock_summary").upsert(
            s, on_conflict="symbol"
        ).execute()
        self.sb.table("last_updated").upsert(
            {"symbol": s["symbol"], "timestamp": s["last_updated"]},
            on_conflict="symbol"
        ).execute()

    # ── FRESHNESS CHECK ──────────────────────────────────
    def _needs_update(self, symbol: str) -> bool:
        resp = (
            self.sb.table("last_updated")
            .select("timestamp")
            .eq("symbol", symbol)
            .execute()
        )
        if not resp.data:
            return True
        last = datetime.fromisoformat(resp.data[0]["timestamp"])
        return (datetime.now() - last) > timedelta(hours=24)

    # ── PUBLIC: FETCH ONE SYMBOL ──────────────────────────
    def fetch(self, symbol: str, force: bool = False) -> pd.DataFrame:
        """
        Fetch + store historical graph data for one NSE symbol.
        Returns OHLCV DataFrame.
        """
        nse_symbol = f"{symbol}:{NSE_EXCHANGE}"

        if not force and not self._needs_update(symbol):
            print(f"[MarketDataAgent] {symbol} up-to-date, loading from DB.")
            return self.load(symbol)

        print(f"[MarketDataAgent] Fetching {symbol} from SerpAPI (multiple windows)...")
        
        windows = ["MAX", "1Y", "1M"]
        all_dfs = []
        summary = {}

        for w in windows:
            data = self._fetch_google_finance(nse_symbol, window=w)
            if data:
                if not summary:
                    summary = self._parse_summary(symbol, data)
                parsed_df = self._parse_graph_to_ohlcv(symbol, data)
                if not parsed_df.empty:
                    all_dfs.append(parsed_df)

        if not all_dfs:
            return pd.DataFrame()

        df = pd.concat(all_dfs, ignore_index=True)
        # Drop duplicate dates, keeping the last (which typically has higher daily resolution from shorter windows)
        df = df.sort_values("date").drop_duplicates(subset=["date"], keep="last").reset_index(drop=True)

        self._save_ohlcv(df)
        if summary:
            self._save_summary(summary)

        print(f"[MarketDataAgent] {symbol}: {len(df)} data points saved.")
        return df

    # ── PUBLIC: LOAD FROM SUPABASE ───────────────────────
    def load(self, symbol: str) -> pd.DataFrame:
        """Load OHLCV from Supabase."""
        resp = (
            self.sb.table("ohlcv")
            .select("*")
            .eq("symbol", symbol)
            .order("date")
            .execute()
        )
        df = pd.DataFrame(resp.data) if resp.data else pd.DataFrame()
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
            df = df.drop_duplicates(subset=["date"]).reset_index(drop=True)
        return df

    def get_summary(self, symbol: str) -> dict:
        """Get latest quote summary for a symbol."""
        resp = (
            self.sb.table("stock_summary")
            .select("*")
            .eq("symbol", symbol)
            .execute()
        )
        if resp.data:
            return resp.data[0]
        return {}

    # ── PUBLIC: RUN FULL BATCH ────────────────────────────
    def run(self, symbols: list = None, force: bool = False):
        """
        Fetch all NIFTY50 symbols.
        Respects SerpAPI rate limits with a delay between calls.
        """
        symbols = symbols or NIFTY50_SYMBOLS
        print(f"[MarketDataAgent] Starting batch fetch: {len(symbols)} symbols")

        for i, symbol in enumerate(symbols):
            self.fetch(symbol, force=force)
            if i < len(symbols) - 1:
                time.sleep(SERPAPI_DELAY_SEC)   # Be polite to the API

        print("[MarketDataAgent] Batch fetch complete.")

    def get_all_symbols(self) -> list:
        resp = self.sb.table("last_updated").select("symbol").execute()
        if not resp.data:
            return []
        return sorted(list({r["symbol"] for r in resp.data}))
