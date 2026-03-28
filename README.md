# 📡 SignalSense AI
**Autonomous Stock Pattern Intelligence Agent**

---

## 🗂️ Project Structure

```
signalsense/
├── agents/
│   ├── market_data_agent.py   # Module 1 — SerpAPI Google Finance
│   ├── pattern_agent.py       # Module 2 — Pattern Detection
│   ├── backtest_agent.py      # Module 3 — Backtesting Engine
│   ├── insight_agent.py       # Module 4 — Groq LLM Insights
│   ├── orchestrator.py        # Module 6 — Pipeline Coordinator
│   └── alerts.py              # Module 7 — Alerts (Console + Telegram)
├── data/
│   └── database.py            # Module 5 — SQLite Interface
├── dashboard/
│   └── app.py                 # Module 8 — Streamlit Dashboard
├── utils/
│   └── config.py              # API keys & settings
├── requirements.txt
└── README.md
```

---

## ⚙️ Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Set API keys
Create a `.env` file in the root:
```env
SERPAPI_KEY=your_serpapi_key_here
GROQ_API_KEY=your_groq_api_key_here

# Optional — for Telegram alerts
TELEGRAM_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id
```

Or export them directly:
```bash
export SERPAPI_KEY="your_key"
export GROQ_API_KEY="your_key"
```

### 3. Run the dashboard
```bash
cd signalsense
streamlit run dashboard/app.py
```

---

## 🔑 APIs Used

| Module | API | Free? |
|--------|-----|-------|
| Market Data | SerpAPI Google Finance | 100 free searches/month |
| Insight Agent | Groq (Llama 3.3 70B) | ✅ Free tier |
| Indicators | numpy + pandas (local) | ✅ Free |
| Storage | SQLite (local) | ✅ Free |
| Dashboard | Streamlit | ✅ Free |
| Alerts | Telegram Bot API | ✅ Free |

---

## 📌 Important Notes on SerpAPI Google Finance

- Symbol format for NSE: `RELIANCE:NSE`
- `window=MAX` gives the maximum historical graph data
- Graph data includes: date, price, volume per day
- High/Low values are estimated (±0.5%) since Google Finance only provides close price in graph
- **Free plan: 100 searches/month** — scan selectively or use cached DB data

---

## 🔁 Pipeline Flow

```
SerpAPI Google Finance
       ↓
  OHLCV stored in SQLite
       ↓
  Pattern Detection (Breakout, Golden Cross, RSI Divergence, Double Bottom)
       ↓
  Backtesting (Win Rate, Avg Return, Drawdown, Risk/Reward)
       ↓
  Groq LLM Insight (Plain-English Action + Sentiment)
       ↓
  Alerts → Console / Telegram
       ↓
  Streamlit Dashboard (Market Radar + Deep Analysis + Activity Log)
```

---

## 📊 Patterns Detected

| Pattern | Signal |
|---------|--------|
| **Breakout** | Close > 20-day high + Volume > 1.5× average |
| **Golden Cross** | SMA50 crosses above SMA200 |
| **RSI Divergence** | Price lower-low, RSI higher-low (bullish momentum reversal) |
| **Double Bottom** | Two lows within 3% of each other with neckline confirmation |

---

*Not financial advice. Always do your own research.*
