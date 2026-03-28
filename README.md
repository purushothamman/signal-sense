# 🚀 SignalSense AI

**SignalSense AI** is an autonomous, scalable financial analysis pipeline that continuously tracks market data, detects advanced technical patterns, scientifically backtests its own findings, and uses cutting-edge LLMs to write actionable, human-like summaries of trade opportunities—all visualized in a stunning **Streamlit Dashboard** and backed by a cloud-native **Supabase (PostgreSQL)** database.

It doesn't just draw lines on charts. It scientifically scores those lines across historical timeframes and asks Artificial Intelligence to justify the trade.

---

## 🧠 How It Works: The Autonomous Agent Pipeline

The platform is powered by a multi-agent architectural pipeline. An `Orchestrator` runs all the agents sequentially over a customizable universe of stock ticker symbols (like `RELIANCE`, `TCS`, `INFY`):

### 1. Market Data Agent (`market_data_agent.py`)
- **What it does**: Silently pulls daily Open-High-Low-Close-Volume (OHLCV) stock data, price quotes, and market caps. 
- **The Tech**: Interfaces with **SerpAPI (Google Finance)** to navigate around complex web hurdles and caches this raw stock data directly into a Supabase PostgreSQL `ohlcv` and `stock_summary` table.

### 2. Pattern Agent (`pattern_agent.py`)
- **What it does**: Runs strict, math-based algorithms over the OHLCV data to detect technical formations.
- **The Models/Formations**: 
  - **Volume Breakouts**: Price punches through the 20-day high on significantly larger-than-average trade volume.
  - **Golden Cross (SMA Crossovers)**: Short-term Simple Moving Average (SMA-10) reliably crosses above a longer-term baseline (SMA-30).
  - **RSI Divergences**: Relative Strength Index deviates from pure price action, signaling a trend reversal.
  - **Double Bottoms**: "W" shaped price recovery patterns showing strong, tested support lines.
- **The Scoring**: Assigns a calculated **Confidence %** (from 50% to 100%) to each detected pattern based on volume multipliers and similarity variances.

### 3. Backtest Agent (`backtest_agent.py`)
- **What it does**: Checks its own historical accuracy immediately. 
- **The Math**: For every new signal detected, it looks backward to find *every other time* that exact signal appeared for that stock. It computes the mathematical **Win Rate** (%), **Average Return** (%), and **Max Drawdown** over the next `N` days following those historical triggers, storing these rigorous statistics globally.

### 4. Insight Agent (`insight_agent.py`)
- **What it does**: Acts as your personal quantitative analyst.
- **The LLM**: Feeds the raw Pattern Data and Backtest Math into a **Groq AI** endpoint (running models like Llama 3) to synthesize a highly structured JSON response. It generates a final `suggested_action` (Buy, Watch, Avoid), `sentiment` (Bullish/Bearish), and a concise written summary explaining the fundamental/technical rationale.

### 5. Alerts Agent (`alerts.py`)
- **What it does**: Continuously monitors the database for "Golden Opportunities" (Signals with extreme confidence thresholds AND high historical win rates) and packages them into high-stakes alerts.

---

## 📊 The Tech Stack

- **Frontend:** Streamlit — A highly responsive, dynamic React-based Python dashboard engine containing:
  - **Market Radar**: A live feed of all generated signals filterable by Action, Pattern, and minimum Confidence.
  - **Deep Analysis**: Interactive `plotly` candlestick charts visualizing prices, SMA overlays, and volume bar graphs.
  - **Portfolio Simulator**: Real-time backtest aggregation letting users filter the most statistically reliable trade setups historically found in the system.
- **Backend Infrastructure:** Supabase (PostgreSQL) — Used to handle heavy data operations, guaranteeing persistence across cloud environments. Includes schemas for `ohlcv`, `signals`, `insights`, and `activity_log`.
- **APIs:** SerpAPI (Market Data fetching) & Groq (Lightning-fast Large Language Model inferencing).

---

## 🛠️ Getting Started / Setup

### Prerequisites
Make sure you have **Python 3.10+** installed.

1. **Clone & Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   *Core dependencies involve `streamlit`, `pandas`, `plotly`, `groq`, `google-search-results` (SerpAPI), and `supabase`.*

2. **Initialize Database**
   - Create a free project on [Supabase](https://supabase.com).
   - Go to the Supabase SQL Editor and run the entire contents of the root `supabase_schema.sql` script to deploy all 8 required database tables.

3. **Set Up Environment Credentials**
   Open your `.env` file (or create one in the root folder) and configure your API keys:
   ```env
   SERPAPI_KEY=your_serpapi_key_here
   GROQ_API_KEY=your_groq_key_here
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your_supabase_service_role_key
   ```
   *(Note: Strongly recommend using the Supabase `service_role` key since the backend does not rely on direct viewer authentication).*

4. **Launch Application!**
   Start the interactive Streamlit engine:
   ```bash
   python -m streamlit run dashboard/app.py
   ```

---

## 📌 Architecture Philosophy

SignalSense AI embodies **quantamental** investing—merging quantitative automation with fundamental AI reasoning. Its design deliberately isolates data fetching, pattern detection, statistical verification, and humanized reasoning into independent, decoupled "Agent" files. This guarantees that if one component breaks (e.g. SerpAPI rate limits), the overarching pipeline and dashboard gracefully fail over and retrieve cached data from Supabase.
