-- ============================================================
-- SignalSense AI — Supabase (PostgreSQL) Schema Migration
-- Run this in your Supabase SQL Editor (https://supabase.com)
-- ============================================================

-- 1. OHLCV — historical price data
CREATE TABLE IF NOT EXISTS ohlcv (
    symbol  TEXT NOT NULL,
    date    TEXT NOT NULL,
    open    DOUBLE PRECISION,
    high    DOUBLE PRECISION,
    low     DOUBLE PRECISION,
    close   DOUBLE PRECISION,
    volume  DOUBLE PRECISION DEFAULT 0,
    PRIMARY KEY (symbol, date)
);

CREATE INDEX IF NOT EXISTS idx_ohlcv_symbol ON ohlcv (symbol);
CREATE INDEX IF NOT EXISTS idx_ohlcv_date   ON ohlcv (date);

-- 2. STOCK SUMMARY — latest quote snapshot
CREATE TABLE IF NOT EXISTS stock_summary (
    symbol       TEXT PRIMARY KEY,
    price        DOUBLE PRECISION,
    change       DOUBLE PRECISION,
    change_pct   DOUBLE PRECISION,
    market_cap   TEXT,
    pe_ratio     DOUBLE PRECISION,
    exchange     TEXT,
    currency     TEXT,
    last_updated TEXT
);

-- 3. LAST UPDATED — freshness tracking
CREATE TABLE IF NOT EXISTS last_updated (
    symbol    TEXT PRIMARY KEY,
    timestamp TEXT
);

-- 4. SIGNALS — detected technical patterns
CREATE TABLE IF NOT EXISTS signals (
    id          BIGSERIAL PRIMARY KEY,
    symbol      TEXT,
    date        TEXT,
    pattern     TEXT,
    confidence  DOUBLE PRECISION,
    details     TEXT,
    created_at  TEXT,
    UNIQUE (symbol, date, pattern)
);

CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals (symbol);
CREATE INDEX IF NOT EXISTS idx_signals_date   ON signals (date);

-- 5. BACKTEST RESULTS — historical pattern performance
CREATE TABLE IF NOT EXISTS backtest_results (
    id                  BIGSERIAL PRIMARY KEY,
    symbol              TEXT,
    pattern             TEXT,
    win_rate            DOUBLE PRECISION,
    avg_return          DOUBLE PRECISION,
    max_drawdown        DOUBLE PRECISION,
    total_occurrences   INTEGER,
    profitable_trades   INTEGER,
    avg_win             DOUBLE PRECISION,
    avg_loss            DOUBLE PRECISION,
    risk_reward         DOUBLE PRECISION,
    created_at          TEXT,
    UNIQUE (symbol, pattern)
);

-- 6. INSIGHTS — AI-generated analysis
CREATE TABLE IF NOT EXISTS insights (
    id           BIGSERIAL PRIMARY KEY,
    symbol       TEXT,
    pattern      TEXT,
    date         TEXT,
    insight_json TEXT,
    created_at   TEXT,
    UNIQUE (symbol, pattern, date)
);

-- 7. ALERTS — pushed notifications
CREATE TABLE IF NOT EXISTS alerts (
    id               BIGSERIAL PRIMARY KEY,
    symbol           TEXT,
    pattern          TEXT,
    date             TEXT,
    confidence       DOUBLE PRECISION,
    win_rate         DOUBLE PRECISION,
    suggested_action TEXT,
    sentiment        TEXT,
    summary          TEXT,
    sent_at          TEXT
);

CREATE INDEX IF NOT EXISTS idx_alerts_sent_at ON alerts (sent_at);

-- 8. ACTIVITY LOG — pipeline execution log
CREATE TABLE IF NOT EXISTS activity_log (
    id        BIGSERIAL PRIMARY KEY,
    timestamp TEXT,
    level     TEXT,
    message   TEXT
);

-- ============================================================
-- Done! All 8 tables created.
-- ============================================================
