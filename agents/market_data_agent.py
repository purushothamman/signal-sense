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
import sqlite3
import time
from datetime import datetime, timedelta
from utils.config import (
    SERPAPI_KEY, SERPAPI_BASE_URL, NSE_EXCHANGE,
    NIFTY50_SYMBOLS, DB_PATH, SERPAPI_DELAY_SEC
)


class MarketDataAgent:
    def __init__(self):
        self.api_key  = SERPAPI_KEY
        self.db_path  = DB_PATH
        self._init_db()

    # ── DATABASE SETUP ───────────────────────────────────
    def _init_db(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS ohlcv (
                symbol  TEXT,
                date    TEXT,
                open    REAL,
                high    REAL,
                low     REAL,
                close   REAL,
                volume  REAL,
                PRIMARY KEY (symbol, date)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS stock_summary (
                symbol          TEXT PRIMARY KEY,
                price           REAL,
                change          REAL,
                change_pct      REAL,
                market_cap      TEXT,
                pe_ratio        REAL,
                exchange        TEXT,
                currency        TEXT,
                last_updated    TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS last_updated (
                symbol    TEXT PRIMARY KEY,
                timestamp TEXT
            )
        """)
        conn.commit()
        conn.close()

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

        return {
            "symbol":       symbol.split(":")[0],
            "price":        price,
            "change":       change.get("amount", 0),
            "change_pct":   change.get("percentage", 0),
            "market_cap":   summary.get("market_cap", ""),
            "pe_ratio":     summary.get("pe_ratio", None),
            "exchange":     summary.get("exchange", NSE_EXCHANGE),
            "currency":     summary.get("currency", "INR"),
            "last_updated": datetime.now().isoformat(),
        }

    # ── SAVE TO DB ───────────────────────────────────────
    def _save_ohlcv(self, df: pd.DataFrame):
        if df.empty:
            return
        df = df.copy()
        df["date"] = pd.to_datetime(df["date"]).dt.tz_localize(None).astype(str)
        conn = sqlite3.connect(self.db_path)
        for _, row in df.iterrows():
            conn.execute("""
                INSERT OR IGNORE INTO ohlcv (symbol, date, open, high, low, close, volume)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (row.symbol, row.date, row.open, row.high, row.low, row.close, row.volume))
        conn.commit()
        conn.close()

    def _save_summary(self, s: dict):
        if not s or not s.get("price"):
            return
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            INSERT OR REPLACE INTO stock_summary
            (symbol, price, change, change_pct, market_cap, pe_ratio, exchange, currency, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (s["symbol"], s["price"], s["change"], s["change_pct"],
              s["market_cap"], s["pe_ratio"], s["exchange"], s["currency"], s["last_updated"]))
        conn.execute("INSERT OR REPLACE INTO last_updated VALUES (?, ?)",
                     (s["symbol"], s["last_updated"]))
        conn.commit()
        conn.close()

    # ── FRESHNESS CHECK ──────────────────────────────────
    def _needs_update(self, symbol: str) -> bool:
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT timestamp FROM last_updated WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return True
        last = datetime.fromisoformat(row[0])
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

    # ── PUBLIC: LOAD FROM DB ──────────────────────────────
    def load(self, symbol: str) -> pd.DataFrame:
        """Load OHLCV from SQLite."""
        conn = sqlite3.connect(self.db_path)
        df = pd.read_sql(
            "SELECT * FROM ohlcv WHERE symbol = ? ORDER BY date ASC",
            conn, params=(symbol,)
        )
        conn.close()
        df["date"] = pd.to_datetime(df["date"], utc=True).dt.tz_localize(None)
        df = df.drop_duplicates(subset=["date"]).reset_index(drop=True)
        return df

    def get_summary(self, symbol: str) -> dict:
        """Get latest quote summary for a symbol."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stock_summary WHERE symbol = ?", (symbol,))
        row = cursor.fetchone()
        conn.close()
        if not row:
            return {}
        cols = ["symbol","price","change","change_pct","market_cap",
                "pe_ratio","exchange","currency","last_updated"]
        return dict(zip(cols, row))

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
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv")
        symbols = [r[0] for r in cursor.fetchall()]
        conn.close()
        return symbols
