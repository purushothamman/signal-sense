"""
Module 4: Insight Generation Agent
Uses Groq (Llama 3.3 70B) to convert raw signal + backtest metrics
into structured plain-English investor guidance.
Output is always JSON with: summary, action, reasoning, risk, sentiment.
"""

import json
from datetime import datetime
from groq import Groq
from utils.config import GROQ_API_KEY, GROQ_MODEL, GROQ_TEMPERATURE, GROQ_MAX_TOKENS
from data.supabase_client import get_client

SYSTEM_PROMPT = """You are SignalSense AI, an expert financial analyst for Indian retail investors.
Convert technical signal data into clear, balanced, plain-English investment insights.
Never guarantee profits. Always mention risks. 
Respond ONLY with valid JSON — no markdown, no code fences, no extra text."""


class InsightAgent:
    def __init__(self):
        self.client = Groq(api_key=GROQ_API_KEY)
        self.sb     = get_client()

    # ── PROMPT BUILDER ───────────────────────────────────
    def _build_prompt(self, signal: dict, backtest: dict) -> str:
        return f"""
Analyze this NSE stock signal and generate a structured investor insight.

SIGNAL:
  Stock   : {signal.get('symbol')}
  Pattern : {signal.get('pattern')}
  Date    : {signal.get('date')}
  Details : {signal.get('details')}
  Confidence : {signal.get('confidence')}%

HISTORICAL BACKTEST (last 2 years, {self._hold()} day hold):
  Win Rate          : {backtest.get('win_rate', 'N/A')}%
  Avg 5-Day Return  : {backtest.get('avg_return', 'N/A')}%
  Avg Winning Trade : +{backtest.get('avg_win', 'N/A')}%
  Avg Losing Trade  : {backtest.get('avg_loss', 'N/A')}%
  Max Drawdown      : {backtest.get('max_drawdown', 'N/A')}%
  Risk/Reward       : {backtest.get('risk_reward', 'N/A')}
  Occurrences       : {backtest.get('total_occurrences', 'N/A')}

Return ONLY this JSON object:
{{
  "summary": "2-3 sentence plain-English explanation of what this signal means",
  "confidence_explanation": "1-2 sentences on why this confidence level",
  "suggested_action": "Buy" or "Watch" or "Avoid",
  "action_reasoning": "1-2 sentences justifying the action",
  "key_risk": "single most important risk to watch out for",
  "time_horizon": "Short-term (3-7 days)" or "Medium-term (2-4 weeks)" or "Monitor only",
  "sentiment": "Bullish" or "Cautiously Bullish" or "Neutral" or "Bearish"
}}"""

    def _hold(self) -> int:
        from utils.config import HOLD_DAYS
        return HOLD_DAYS

    # ── LLM CALL ─────────────────────────────────────────
    def generate(self, signal: dict, backtest: dict) -> dict:
        prompt = self._build_prompt(signal, backtest)
        try:
            response = self.client.chat.completions.create(
                model=GROQ_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                temperature=GROQ_TEMPERATURE,
                max_tokens=GROQ_MAX_TOKENS,
            )
            raw = response.choices[0].message.content.strip()

            # Strip accidental markdown fences
            if "```" in raw:
                parts = raw.split("```")
                raw = parts[1] if len(parts) > 1 else parts[0]
                if raw.startswith("json"):
                    raw = raw[4:]
            raw = raw.strip()

            return json.loads(raw)

        except json.JSONDecodeError as e:
            print(f"[InsightAgent] JSON parse error ({signal.get('symbol')}): {e}")
            return self._fallback(signal, backtest)
        except Exception as e:
            print(f"[InsightAgent] Groq error: {e}")
            return self._fallback(signal, backtest)

    # ── RULE-BASED FALLBACK ───────────────────────────────
    def _fallback(self, signal: dict, backtest: dict) -> dict:
        wr     = backtest.get("win_rate", 50) or 50
        action = "Buy" if wr > 65 else "Watch" if wr > 50 else "Avoid"
        return {
            "summary":                f"{signal.get('pattern')} detected on {signal.get('symbol')}. Historical win rate: {wr}%.",
            "confidence_explanation": f"Based on {backtest.get('total_occurrences', 0)} historical occurrences.",
            "suggested_action":       action,
            "action_reasoning":       f"Win rate of {wr}% {'supports' if wr > 60 else 'does not strongly support'} a position.",
            "key_risk":               "Market conditions may differ from historical patterns.",
            "time_horizon":           "Short-term (3-7 days)",
            "sentiment":              "Cautiously Bullish" if wr > 55 else "Neutral",
        }

    # ── CACHE ─────────────────────────────────────────────
    def _get_cached(self, symbol: str, pattern: str, date: str) -> dict:
        resp = (
            self.sb.table("insights")
            .select("insight_json")
            .eq("symbol", symbol)
            .eq("pattern", pattern)
            .eq("date", date)
            .execute()
        )
        if resp.data:
            return json.loads(resp.data[0]["insight_json"])
        return {}

    def _save(self, symbol: str, pattern: str, date: str, insight: dict):
        self.sb.table("insights").upsert({
            "symbol":       symbol,
            "pattern":      pattern,
            "date":         date,
            "insight_json": json.dumps(insight),
            "created_at":   datetime.now().isoformat(),
        }, on_conflict="symbol,pattern,date").execute()

    # ── PUBLIC RUN ───────────────────────────────────────
    def run(self, signal: dict, backtest: dict) -> dict:
        """Generate (or return cached) insight for a signal."""
        symbol  = signal.get("symbol")
        pattern = signal.get("pattern")
        date    = signal.get("date")

        cached = self._get_cached(symbol, pattern, date)
        if cached:
            print(f"[InsightAgent] Cache hit: {symbol} | {pattern}")
            return cached

        print(f"[InsightAgent] Generating: {symbol} | {pattern}...")
        insight = self.generate(signal, backtest)
        self._save(symbol, pattern, date, insight)
        print(f"[InsightAgent] → Action: {insight.get('suggested_action')} | "
              f"Sentiment: {insight.get('sentiment')}")
        return insight
